"""Bounded G3 registration and detector-side parity for admitted application views.

Ported from lab/g3-camera-registration at f0884a8. Pixel coordinates are
normalized to a 384 square, MakeHuman coordinates to centimetres. Application
admission owns the camera sector, pose constraints and scale provenance.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from .experimental_camera import Camera
from .native_rig import rebind_joints, skin_vertices

SEGMENTS = ('upperarm01.L','lowerarm01.L','upperarm01.R','lowerarm01.R',
            'upperleg01.L','lowerleg01.L','upperleg01.R','lowerleg01.R')
TOKENS = {11:SEGMENTS[0],13:SEGMENTS[1],15:'wrist.L',12:SEGMENTS[2],
          14:SEGMENTS[3],16:'wrist.R',23:SEGMENTS[4],25:SEGMENTS[5],27:'foot.L',
          24:SEGMENTS[6],26:SEGMENTS[7],28:'foot.R'}
INDEX = tuple(sorted(TOKENS))
POSE_KEYS = tuple((name,axis) for name in SEGMENTS for axis in ('z','pitch'))
FIT_SIZE = 384


class Rig:
    def __init__(self, rig, neutral):
        self.rig = rig
        self.vertices = np.asarray(neutral).copy()
        self.vertices.flags.writeable = False
        self.joints = rebind_joints(rig, self.vertices)
        self.bones = rig['bones']
        self.required = set()
        for bone in TOKENS.values():
            while bone and bone not in self.required:
                self.required.add(bone)
                bone = self.bones[bone]['parent']
        skin_indices = np.array([i for i,w in enumerate(rig['skin']) if w])
        active = self.vertices[skin_indices]
        lo,hi = active[:,1].min(),active[:,1].max()
        face = active[(active[:,1]>hi-.095*(hi-lo)) & (active[:,1]<hi-.049*(hi-lo)) & (abs(active[:,0])<3)]
        self.face_pointer = face[np.argmax(face[:,2])] if len(face) else active[np.argmax(active[:,1])]
        self.root_order = self.order(self.required)
        self.full_order = self.order(self.bones)

    def order(self, bones):
        order = {}
        def insert(name):
            if name is None or name in order:
                return
            insert(self.bones[name]['parent'])
            order[name] = self.bones[name]
        for name in sorted(bones):
            insert(name)
        return tuple(order.items())

    def transforms(self, pose, order):
        params = np.asarray(pose).reshape(-1,2)
        local = {}
        for name,(turn,pitch) in zip(SEGMENTS,params):
            bone = self.bones[name]
            v = self.joints[bone['tail']] - self.joints[bone['head']]
            horizontal = np.cross(v,[0,0,1.])
            horizontal /= max(np.linalg.norm(horizontal),1e-8)
            local[name] = Rotation.from_rotvec([0,0,turn]).as_matrix() @ Rotation.from_rotvec(pitch*horizontal).as_matrix()
        result = {}
        for name,bone in order:
            parent = bone['parent']
            r,t = result[parent] if parent else (np.eye(3),np.zeros(3))
            if name in local:
                head = self.joints[bone['head']]
                composed = r @ local[name]
                t,r = t+(r-composed)@head,composed
            result[name] = r,t
        return result

    def anchors(self, pose):
        transforms = self.transforms(pose,self.root_order)
        return np.array([transforms[TOKENS[i]][0]@self.joints[self.bones[TOKENS[i]]['head']]
                         + transforms[TOKENS[i]][1] for i in INDEX])

    def mesh(self, pose):
        return skin_vertices(self.vertices,self.rig['skin'],self.transforms(pose,self.full_order))


@dataclass(frozen=True)
class Observation:
    xy: np.ndarray
    confidence: np.ndarray
    mask: np.ndarray
    excluded: np.ndarray
    focal_px_prior: float | None = None
    scale_cm_per_model_unit: float | None = None
    signed_yaw_prior: float | None = None
    nose_hint: tuple | None = None
    capture_yaw_sector: float | None = None


def camera(parameters, perspective):
    yaw,pitch,roll,log_span,log_distance,shift_x,shift_y = parameters[:7]
    return Camera(yaw=np.degrees(yaw),elevation=np.degrees(pitch),roll=np.degrees(roll),
                  span=float(np.exp(log_span)),distance=float(np.exp(log_distance)),
                  dx=shift_x,dy=shift_y,perspective=perspective)


def angle_error(a,b):
    return (a-b+180)%360-180


def raster_iou(raster, cam, posed, faces, obs):
    size = len(obs.mask)
    pred = raster.draw(cam,posed,faces,size)
    valid = ~obs.excluded
    return float((pred & obs.mask & valid).sum()/max(1,((pred|obs.mask)&valid).sum()))


def scale_certificate(obs, fit_camera):
    if obs.scale_cm_per_model_unit is None:
        return dict(metric=False, distance_cm=None, reason='similarity gauge: uniform size and translation scaling')
    return dict(metric=bool(fit_camera.perspective and obs.focal_px_prior is not None),
                distance_cm=fit_camera.distance*obs.scale_cm_per_model_unit if fit_camera.perspective and obs.focal_px_prior is not None else None,
                reason='external body scale plus focal prior; depth remains prior-conditional')


def solve(rig, obs, faces, raster, indices=None, articulate=True, perspective=True,
          calibrated_camera=None, checkpoint=lambda: None):
    if obs.xy.shape!=(len(INDEX),2) or obs.confidence.shape!=(len(INDEX),):
        raise ValueError('invalid landmarks')
    valid = np.isfinite(obs.xy).all(axis=1) & (obs.confidence>.05)
    if indices is not None:
        valid &= indices
    if valid.sum()<5:
        return {'status':'insufficient_landmarks','usable':int(valid.sum())}
    base_pose = np.zeros(len(POSE_KEYS))
    preferred = obs.signed_yaw_prior
    sector = obs.capture_yaw_sector
    guesses = [0,60,120,180,-120,-60] if preferred is None else [preferred,preferred+180,preferred-60,preferred+60]
    if sector is not None:
        guesses = [sector]
    valid_y,valid_x = np.where(obs.mask & ~obs.excluded)
    span = 215.
    shift = np.zeros(2)
    if len(valid_x):
        span = np.clip(np.ptp(rig.vertices[:,1])*FIT_SIZE/max(1,np.ptp(valid_y)),138,415)
        shift = np.array([(valid_x.min()+valid_x.max())/2,(valid_y.min()+valid_y.max())/2])/FIT_SIZE-.5
    distance = (obs.focal_px_prior or 660)*span/FIT_SIZE
    count = 7+len(base_pose) if articulate else 7
    weights = np.sqrt(np.clip(obs.confidence[valid],.05,1))/4
    hypotheses = []
    for guess in (guesses if calibrated_camera is None else [calibrated_camera.yaw]):
        checkpoint()
        seed = np.r_[np.deg2rad([guess,0.,0.]),np.log([span,distance]),shift,
                     base_pose if articulate else []]
        offset = 7 if calibrated_camera is not None else 0
        half_width = np.deg2rad(48) if sector is not None else np.pi/2
        low = np.r_[seed[0]-half_width,-.70,-.55,np.log(110),np.log(155),-.40,-.40,
                    np.full(count-7,-1.2)]
        high = np.r_[seed[0]+half_width,.70,.55,np.log(550),np.log(1800),.40,.40,
                     np.full(count-7,1.2)]

        def evaluate(z, prior=True):
            checkpoint()
            full = np.r_[seed[:offset],z]
            cam = calibrated_camera or camera(full,perspective)
            pose = full[7:] if articulate else base_pose
            expected = cam.project(rig.anchors(pose),FIT_SIZE)[valid,:2]
            resid = ((expected-obs.xy[valid])*weights[:,None]).ravel()
            if not prior:
                return resid
            terms = []
            if calibrated_camera is None:
                focal = FIT_SIZE*cam.distance/cam.span
                # Focal uncertainty stays explicit. 660 px is only a weak default.
                terms.extend([np.log(focal/(obs.focal_px_prior or 660))/(.09 if obs.focal_px_prior else .45)
                              if perspective else (full[4]-seed[4])/.02,
                              full[1]/.36,full[2]/.26,full[5]/.25,full[6]/.25])
                if preferred is not None and sector is None:
                    terms.append(angle_error(cam.yaw,preferred)/36)
            if articulate:
                terms.extend((pose/np.tile([.8,.45],len(SEGMENTS))).tolist())
            return np.r_[resid,terms]

        if count==offset:
            fitted = None
            params = seed
            raw_error = evaluate([],False)
            cost = float(np.mean(raw_error**2))
        else:
            fitted = least_squares(evaluate,np.clip(seed[offset:],low[offset:]+1e-5,high[offset:]-1e-5),
                                   bounds=(low[offset:],high[offset:]),loss='soft_l1',f_scale=1.5,
                                   max_nfev=36,ftol=1e-4,xtol=1e-4)
            params = np.r_[seed[:offset],fitted.x]
            cost = float(2*fitted.cost/max(1,valid.sum()*2))
        cam = calibrated_camera or camera(params,perspective)
        pose = params[7:] if articulate else base_pose
        fit_iou = raster_iou(raster,cam,rig.mesh(pose),faces,obs)
        face_cost = 0.
        if obs.nose_hint is not None:
            x,y,weight = obs.nose_hint
            nose = cam.project(rig.face_pointer[None,:],FIT_SIZE)[0,:2]
            face_cost = .35*weight*min(1.,np.linalg.norm(nose-[x,y])/18)
            face_cost += .50*weight*max(0.,-cam.axes()[2,2])
        score = cost+4*(1-fit_iou)+face_cost
        hypotheses.append((score,cam,pose,fitted,evaluate(fitted.x if fitted else [],False),fit_iou))
    hypotheses.sort(key=lambda h:h[0])
    score,cam,pose,result,resid,fit_iou = hypotheses[0]
    covariance = np.zeros((7,7))
    effective_rank = 0
    if result is not None and calibrated_camera is None:
        j = result.jac
        s = np.linalg.svd(j[:2*valid.sum()], compute_uv=False)
        effective_rank = int((s>s[0]*1e-4).sum()) if len(s) and s[0] else 0
        variance = max(1.,float(np.mean(resid**2)))
        cov = np.linalg.pinv(j.T@j,rcond=1e-10)*variance
        covariance = cov[:7,:7]
    alternatives = [{'yaw_deg':float(angle_error(h[1].yaw,0)), 'score':h[0], 'iou':h[-1]} for h in hypotheses]
    competitors = [h for h in alternatives[1:] if abs(angle_error(h['yaw_deg'],cam.yaw))>55]
    return dict(status='ok',camera=cam,pose=pose,cost=score,iou=fit_iou,
                ambiguity_gap=(competitors[0]['score']-score) if competitors else None,
                covariance=covariance,effective_data_rank=effective_rank,
                alternatives=alternatives,used=valid,scale=scale_certificate(obs,cam))


def select_landmark_parity(rig, observation, faces, raster, indices, **kwargs):
    """Score both detector-side assignments. Surface labels never change with source convention."""
    from dataclasses import replace
    order = [INDEX.index(i+1 if i%2 else i-1) for i in INDEX]
    alternatives = []
    for parity in ('native','swapped'):
        obs = observation
        if parity=='swapped':
            obs = replace(obs,xy=obs.xy[order],confidence=obs.confidence[order],
                          signed_yaw_prior=None if obs.signed_yaw_prior is None else obs.signed_yaw_prior+180)
        result = solve(rig,obs,faces,raster,indices=indices,**kwargs)
        if result['status']=='ok':
            alternatives.append((result['cost'],parity,result))
    if not alternatives:
        return {'status':'insufficient_landmarks'}
    alternatives.sort(key=lambda row:row[0])
    cost,parity,result = alternatives[0]
    return result | {'detector_parity':parity,
                     'parity_gap':alternatives[1][0]-cost if len(alternatives)>1 else None,
                     'parity_alternatives':[
                         {'parity':kind,'cost':score,'yaw_deg':float(angle_error(fit['camera'].yaw,0))}
                         for score,kind,fit in alternatives]}


def anchor_projection_std(rig,result):
    """Prior-conditional camera contribution to per-anchor RMS uncertainty."""
    cam,pose = result['camera'],result['pose']
    params = np.r_[np.deg2rad([cam.yaw,cam.elevation,cam.roll]), np.log([cam.span,cam.distance]),cam.dx,cam.dy]
    points = rig.anchors(pose)
    def project(values):
        return camera(values,cam.perspective).project(points,FIT_SIZE)[:,:2]
    h = 1e-4
    columns = [(project(params+delta)-project(params-delta))/(2*h) for delta in np.eye(7)*h]
    jac = np.stack(columns,axis=-1)
    return np.sqrt(np.maximum(0,np.einsum('nci,ij,ncj->n',jac,result['covariance'],jac)))
