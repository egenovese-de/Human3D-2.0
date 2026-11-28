"""Target-independent native anatomy fitting across registered observations."""
from copy import copy
from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter

import cv2
import numpy as np
from scipy.optimize import minimize

from evidence import State, edge, edge_distance, gaps
from human3d.native_rig import rebind_joints, validate_rebind
from projection import Camera
from registration import Rig, POSE_KEYS


@dataclass(frozen=True)
class RegisteredView:
    key: str
    camera: Camera
    mask: np.ndarray
    states: np.ndarray
    confidence: np.ndarray
    camera_source: str
    scale_source: str
    pose: np.ndarray | None = None
    registration_sigma_px: float = 0.
    alternatives: tuple = ()
    outer_only: np.ndarray | None = None

    def __post_init__(self):
        if self.mask.ndim != 2 or self.mask.shape[0] != self.mask.shape[1] or not self.mask.size:
            raise ValueError('a square normalized raster is required')
        if self.states.shape!=self.mask.shape or self.confidence.shape!=self.mask.shape:
            raise ValueError('evidence map dimensions differ')
        if not np.isin(self.states,list(State)).all():
            raise ValueError('invalid map state')
        if not np.isfinite(self.confidence).all() or np.any((self.confidence<0)|(self.confidence>1)):
            raise ValueError('invalid confidence map')
        if not np.isfinite(self.registration_sigma_px) or self.registration_sigma_px<0:
            raise ValueError('invalid registration uncertainty')
        if self.pose is not None and (self.pose.shape!=(len(POSE_KEYS),) or not np.isfinite(self.pose).all()):
            raise ValueError('invalid observation pose')
        if self.outer_only is not None and self.outer_only.shape!=self.mask.shape:
            raise ValueError('invalid garment extent')
        if not np.isfinite(self.camera.project(np.zeros((1,3)),384)).all() or self.camera.span<=0 or self.camera.distance<=0:
            raise ValueError('invalid camera')


def digest(view):
    data=np.ascontiguousarray(view.mask).tobytes()+np.ascontiguousarray(view.states).tobytes()
    data += np.ascontiguousarray(view.confidence).tobytes()
    if view.outer_only is not None:
        data += np.ascontiguousarray(view.outer_only).tobytes()
    if view.pose is not None:
        data += np.ascontiguousarray(view.pose).tobytes()
    return sha256(data+repr(view.camera).encode()).hexdigest()


def admitted(views):
    dropped, eligible, seen = {}, [], set()
    for view in sorted(views,key=lambda item:item.key):
        if view.camera_source not in ('calibrated','external_sector','calibrated_sector_control'):
            dropped[view.key] = 'unresolved_orientation'
            continue
        if not (view.mask & (view.states!=State.UNOBSERVED)).any():
            dropped[view.key] = 'no_visible_foreground'
            continue
        ident=digest(view)
        if ident in seen:
            dropped[view.key] = 'duplicate_observation'
            continue
        eligible.append(view)
        seen.add(ident)
    return eligible, dropped


def resized(data, n):
    return cv2.resize(data.astype(np.float32),(n,n),interpolation=cv2.INTER_NEAREST_EXACT)


class ImageLoss:
    def __init__(self, view, resolution):
        self.view = view
        self.target = resized(view.mask,resolution)>.5
        states=resized(view.states,resolution)
        self.valid = states!=State.UNOBSERVED
        self.outer = resized(view.outer_only,resolution)>.5 if view.outer_only is not None else np.zeros_like(self.valid)
        self.contour_valid = self.valid & ~self.outer
        self.label_weight = (.3+.7*resized(view.confidence,resolution)) * np.where(states==State.UNCERTAIN,.35,1)
        self.boundary=edge(self.target)&self.contour_valid
        self.outward=edge_distance(self.target)
        self.gap=gaps(self.target)&(states==State.BACKGROUND)&self.contour_valid
        self.area=max(1,int((self.target&self.valid).sum()))
        self.tolerance=min(3.,view.registration_sigma_px*resolution/view.mask.shape[0]*.35)
        self.resolution=resolution

    def __call__(self, candidate, mode):
        delta=candidate^self.target
        # Loose clothing only limits protrusion outside the visible outer envelope.
        valid=self.valid & (~self.outer | ~self.target)
        union=(candidate|self.target)&valid
        iou=1-((candidate&self.target)&valid).sum()/max(1,union.sum())
        if mode=='iou':
            return iou
        contour=edge(candidate)&self.contour_valid
        # Use a common scale for losses from different pyramid levels.
        scale=.065*self.resolution
        if not self.boundary.any():
            region_cost=0.
        elif not contour.any():
            region_cost=1.
        else:
            backward=edge_distance(candidate)
            a=(np.minimum(np.maximum(self.outward[contour]-self.tolerance,0),scale)**2).mean()
            b=(np.minimum(np.maximum(backward[self.boundary]-self.tolerance,0),scale)**2).mean()
            region_cost=(np.sqrt(a)+np.sqrt(b))/(2*scale)
        occupancy=self.label_weight[delta&valid].sum()/self.area
        return float(region_cost+.16*occupancy+.33*(candidate&self.gap).sum()/self.area+.14*iou)


class NativeBasis:
    def __init__(self, engine, settings):
        self.engine=engine
        self.names=tuple(settings['g1_fields'])
        self.home=np.asarray(settings['g1_initial'],float)
        self.bounds=np.asarray(settings['g1_bounds'],float)
        self.global_fields=[i for i,k in enumerate(self.names) if engine.mods[k][0].isMacro()]
        self.regional_fields=[i for i,k in enumerate(self.names) if not engine.mods[k][0].isMacro()]

    def evaluate(self, parameters):
        return self.engine.extended(dict(zip(self.names,parameters)))*10

    def validate(self, canonical):
        validate_rebind(self.engine.body,canonical/10)


class AnatomicalFitter:
    """One canonical vector, with fixed per-view registration and bounded native controls."""
    def __init__(self, basis, raster, faces):
        self.basis=basis
        self.raster=raster
        self.faces=faces

    def fit(self, views, *, mode='contour', budget=650, levels=(112,192), robust=True,
            multistart=True, allow_unanchored_height=False):
        if budget<80 or not levels:
            raise ValueError('insufficient optimizer configuration')
        start=perf_counter()
        views,dropped=admitted(views)
        if not views:
            return None,dict(status='abstained',reason='no_resolved_observation',excluded=dropped)
        weights=np.asarray([1/(1+(v.registration_sigma_px/9)**2) for v in views])
        calls=0
        stage_log=[]
        checkpoints=[]
        basis=self.basis
        independently_scaled=any(v.scale_source=='independent_metric' for v in views)
        locked=[i for i,name in enumerate(basis.names) if name.endswith('/Height') or name.lower().endswith('height')]
        locked=locked if not independently_scaled and not allow_unanchored_height else []
        global_fields=[i for i in basis.global_fields if i not in locked]
        regional_fields=[i for i in basis.regional_fields if i not in locked]
        has_pose=any(v.pose is not None and np.any(v.pose) for v in views)
        template=Rig(basis.engine.body['rig'],basis.evaluate(basis.home)) if has_pose else None
        skin={}
        if template is not None:
            for index, influences in enumerate(template.rig['skin']):
                for bone,weight in influences.items():
                    skin.setdefault(bone,[]).append((index,weight))
        packed={bone:(rows[:,0].astype(int),rows[:,1,None]) for bone,values in skin.items() for rows in [np.asarray(values)]}
        applied=np.unique(np.concatenate([indices for indices,_ in packed.values()])) if packed else None

        def pose_mesh(rig, pose):
            transforms=rig.transforms(pose,rig.full_order)
            points=rig.vertices.copy()
            points[applied]=0.
            for bone,(indices,weight) in packed.items():
                rotation,translation=transforms[bone]
                points[indices] += (rig.vertices[indices]@rotation.T+translation)*weight
            return points

        def objective(resolution):
            maps=[ImageLoss(v,resolution) for v in views]
            def calculate(x):
                nonlocal calls
                calls+=1
                mesh=basis.evaluate(x)
                rig=copy(template) if template is not None else None
                if rig is not None:
                    rig.vertices=mesh
                    rig.joints=rebind_joints(rig.rig,mesh)
                costs=[]
                for prepared in maps:
                    v=prepared.view
                    points=pose_mesh(rig,v.pose) if rig is not None and v.pose is not None and np.any(v.pose) else mesh
                    mask=self.raster.draw(v.camera,points,self.faces,resolution)
                    costs.append(prepared(mask,mode))
                costs=np.asarray(costs)
                if robust and len(costs)>2:
                    costs=.22*np.log1p(costs/.22)
                return float(np.average(costs,weights=weights)+.0015*np.mean((x-basis.home)**2))
            return calculate

        def sweep(x, fields, steps, loss, limit):
            x=x.copy()
            best=loss(x)
            for step in steps:
                for i in fields:
                    if calls+2>limit:
                        return x,best
                    base=x[i]
                    for sign in (-1,1):
                        trial=x.copy()
                        trial[i]=np.clip(base+sign*step,basis.bounds[0,i],basis.bounds[1,i])
                        if trial[i]==x[i]:
                            continue
                        value=loss(trial)
                        if value<best-1e-9:
                            x,best=trial,value
            return x,best
        low=objective(levels[0])
        final=objective(levels[-1])
        seed=basis.home.copy()
        starts=[seed]
        if multistart and global_fields:
            for value in (.20,.80):
                other=seed.copy()
                other[global_fields[0]]=value
                starts.append(other)
        fitted=[]
        cap=int(.34*budget)
        for j,candidate in enumerate(starts):
            vec,val=sweep(candidate,global_fields,(.24,.12,.06),low, min(cap,calls+cap//len(starts)))
            fitted.append((val,vec))
        fitted.sort(key=lambda row:row[0])
        initials=fitted[:min(2,len(fitted))]
        for _,point in initials:
            checkpoints.append(point.copy())
        regional_cap=int(.61*budget)
        refined=[]
        for _,point in initials:
            x,val=sweep(point,global_fields+regional_fields,(.14,.074,.035),low,
                        min(regional_cap,calls+(regional_cap-cap)//len(initials)+18))
            refined.append((val,x))
            checkpoints.append(x.copy())
        stage_log.append(dict(stage='coarse_search',calls=calls,best=min(v for v,_ in refined)))
        refined.sort(key=lambda row:row[0])
        x=refined[0][1]
        x,value=sweep(x,global_fields+regional_fields,(.060,.036,.018),final,int(.86*budget))
        checkpoints.append(x.copy())
        stage_log.append(dict(stage='fine_joint_sweep',calls=calls,best=value))

        # A bounded joint search captures correlated moves left over after coordinate passes.
        dims=global_fields[:6]
        remaining=budget-calls-len(checkpoints)-5
        if dims and remaining>24:
            def joint(values):
                proposal=x.copy()
                proposal[dims]=values
                return final(proposal)
            opt=minimize(joint,x[dims],method='Powell',bounds=basis.bounds[:,dims].T,
                         options={'maxfev':remaining,'xtol':.015,'ftol':.001})
            candidate=x.copy()
            candidate[dims]=opt.x
            checkpoints.append(candidate)
        checkpoints.append(seed)
        ranked=sorted(((final(z),z) for z in checkpoints),key=lambda row:row[0])
        invalid=[]
        for rank,(loss,parameters) in enumerate(ranked):
            mesh=basis.evaluate(parameters)
            try:
                basis.validate(mesh)
            except ValueError as exc:
                invalid.append(str(exc))
                continue
            return mesh,dict(status='ok',canonical_sha256=sha256(mesh.tobytes()).hexdigest(),objective=loss,
                             parameters=dict(zip(basis.names,parameters.tolist())),calls=calls,
                             seconds=perf_counter()-start,views=[v.key for v in views],excluded=dropped,
                             projection_sources={v.key:v.camera_source for v in views},
                             scale_sources={v.key:v.scale_source for v in views},metric_scale=independently_scaled,
                             locked_controls=[basis.names[i] for i in locked],
                             weights=dict(zip([v.key for v in views],weights.tolist())),checkpoints_rejected=invalid,
                             checkpoint_rank=rank,stages=stage_log)
        return None,dict(status='abstained',reason='no_structurally_valid_checkpoint',excluded=dropped,
                         checkpoints_rejected=invalid,calls=calls,seconds=perf_counter()-start)
