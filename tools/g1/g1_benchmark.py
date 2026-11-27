"""G1 controlled equivalence, sensitivity, and geometry-oracle benchmark."""
import argparse
import hashlib
import json
import os
from pathlib import Path
try:
    import resource
except ImportError:
    resource = None
import time
from types import SimpleNamespace
import numpy as np
numpy_unique = np.unique
from scipy.optimize import least_squares, lsq_linear
from scipy.spatial import cKDTree, ConvexHull
from PIL import Image, ImageDraw
import skeleton
from core import G

from g1_engine import Engine
from human3d.proportions import length_controls, lengthen
from human3d.regional_morphs import regional_controls, apply_regional_controls
from human3d.face import widen_head, widen_jaw
from human3d.native_rig import validate_rebind, validate_pose, skin_vertices, pose_transforms
from human3d.alignment import Alignment, Camera
# MakeHuman installs a legacy NumPy shim at import. Keep the modern public API for the audit.
np.unique = numpy_unique

def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False)+"\n")

def summary(values):
    return {k:float(v) for k,v in zip(("mean","median","p95","max","rmse"),
        (np.mean(values),np.median(values),np.percentile(values,95),np.max(values),np.sqrt(np.mean(values**2))))}

def triangulate(faces):
    return np.asarray([(f[0],f[i],f[i+1]) for f in faces for i in range(1,len(f)-1)])

def sample(points, triangles, count, seed):
    t=points[triangles]
    area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)
    rng=np.random.default_rng(seed)
    chosen=rng.choice(len(t),count,p=area/area.sum())
    w=rng.random((count,2))
    w=np.where(w.sum(1)[:,None]>1,1-w,w)
    return t[chosen,0]+w[:,0,None]*(t[chosen,1]-t[chosen,0])+w[:,1,None]*(t[chosen,2]-t[chosen,0])

def metrics(points, triangles):
    faces=points[triangles]
    ext=np.ptp(faces.reshape(-1,3),axis=0)
    twice=np.linalg.norm(np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]),axis=1)
    edges=np.sort(np.vstack([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[0,2]]]),axis=1)
    closed=bool(np.all(np.unique(edges,axis=0,return_counts=True)[1]==2))
    volume=abs(np.einsum('ij,ij->i',faces[:,0],np.cross(faces[:,1],faces[:,2])).sum()/6)
    return dict(box_cm=ext.tolist(), area_cm2=float(twice.sum()/2), volume_l=float(volume/1000) if closed else None,
                closed=closed, finite=bool(np.isfinite(points).all()), near_degenerate=int(np.sum(twice<1e-8)))

def section(points,triangles,y):
    t=points[triangles]
    cuts=[]
    for a,b in ((0,1),(1,2),(2,0)):
        p,q=t[:,a],t[:,b]
        hit=(p[:,1]>y)!=(q[:,1]>y)
        p,q=p[hit],q[hit]
        u=(y-p[:,1])/(q[:,1]-p[:,1])
        cuts.extend((p+(q-p)*u[:,None])[:,[0,2]])
    x=np.asarray(cuts)
    if len(x)<3: return [0.]*5
    hull=ConvexHull(x)
    return [float(np.ptp(x[:,0])),float(np.ptp(x[:,1])),float(x[:,1].max()),float(x[:,1].min()),float(hull.area)]

def measurements(points, triangles, levels):
    return np.asarray([section(points,triangles,y) for y in levels])

def masks(points,faces,center,scale,size=192):
    output=[]
    for angle in (0,90,180,45,135):
        a=np.deg2rad(angle)
        x=(points[:,0]-center[0])*np.cos(a)-(points[:,2]-center[2])*np.sin(a)
        y=points[:,1]-center[1]
        xy=np.rint(np.c_[x,-y]*scale+size/2).astype(int)
        im=Image.new("1",(size,size))
        draw=ImageDraw.Draw(im)
        for face in faces:
            draw.polygon([tuple(i) for i in xy[face]],fill=1)
        output.append(np.array(im))
    return output

def native_rig(e, points):
    mock=SimpleNamespace(getRestposeCoordinates=lambda: points.astype(np.float32))
    G.app=SimpleNamespace(selectedHuman=mock)
    native=skeleton.load(str(e.rig_path),e.mesh)
    ours=validate_rebind(e.body,points)
    joints={k:native.getJointPosition(k,mock) for k in ours}
    delta=np.array([np.linalg.norm(joints[k]-ours[k])*100 for k in ours])
    lengths=[]
    for name,b in e.body["rig"]["bones"].items():
        lengths.append(abs(np.linalg.norm(ours[b["tail"]]-ours[b["head"]])-native.bones[name].length)*100)
    alignment=Alignment(Camera(0,1,0j,1),0,{"lowerarm01.L":.35,"upperarm01.R":-.25})
    posed=skin_vertices(points,e.body["rig"]["skin"],pose_transforms(e.body["rig"],ours,alignment))
    validate_pose(e.body,points,posed)
    raw_weights=native.vertexWeights.data
    ours=e.body["rig"]["skin"]
    delta_weights=[]
    for name,(indices,weights) in raw_weights.items():
        delta_weights.extend(abs(ours[i].get(name,0)-w) for i,w in zip(indices,weights) if i in e.skin_set)
    return {"joint_mm":summary(delta),"bone_length_mm":summary(np.asarray(lengths)),
            "bone_count":len(native.bones),"pose_valid":True,
            "skin_weight_max_error_listed_body_entries":float(max(delta_weights)),
            "uv_max_abs_error":float(np.max(np.abs(np.asarray(e.body["mesh"]["texcoords"])-e.mesh.texco)))}

def custom(e,x,values):
    for name in length_controls(e.body):
        if name in values:
            x=np.asarray(lengthen(e.body,x,name,values[name]))
    regional={k:v for k,v in values.items() if k in regional_controls(e.body)}
    if regional: x=np.asarray(apply_regional_controls(e.body,x,regional))
    if "head_width" in values: x=np.asarray(widen_head(e.body,x,values["head_width"]))
    if "jaw_width" in values: x=np.asarray(widen_jaw(e.body,x,values["jaw_width"]))
    return x

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output",required=True,type=Path)
    a.add_argument("--independent",type=Path)
    a.add_argument("--inventory-only",action="store_true")
    args=a.parse_args()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    e=Engine()
    dump(out/"G1_MODIFIER_INVENTORY.json",e.inventory())
    if args.inventory_only: return
    print("INVENTORY",len(e.mods),len(e.paths),flush=True)
    e.rig_path=Path(os.environ["U"])/"data/rigs/default.mhskel"
    e.skin_set=set(e.skin)
    body_tri=triangulate(e.faces)
    global_names=[e.mac[n] for n in ("Gender","Age","Weight","Muscle","Height","BodyProportions","BreastSize","BreastFirmness")]
    regional=[]
    for k,(m,_) in e.mods.items():
        if m.isMacro() or not e.defs[k]: continue
        if m.groupName in {"torso","stomach","buttocks","hip","pelvis","breast","neck","armslegs","head","measure"}:
            if any(s in k for s in ("scale","circ","shoulder","depth","width","vshape","belly","volume","firm","length","forward","point","tone")):
                regional.append(k)
    # A bounded screen keeps the optimizer tractable. Symmetry-paired and face fields remain in the inventory.
    names=(
        "torso/torso-scale-depth-decr|incr","torso/torso-scale-horiz-decr|incr",
        "torso/torso-scale-vert-decr|incr","torso/torso-vshape-decr|incr",
        "stomach/stomach-pregnancy-decr|incr","buttocks/buttocks-volume-decr|incr",
        "pelvis/pelvis-scale-depth-decr|incr","hip/hip-scale-horiz-decr|incr",
        "measure/measure-bust-circ-decr|incr","measure/measure-waist-circ-decr|incr",
        "measure/measure-shoulder-dist-decr|incr","measure/measure-hips-circ-decr|incr",
        "measure/measure-thigh-circ-decr|incr","measure/measure-calf-circ-decr|incr",
        "measure/measure-upperarm-circ-decr|incr","neck/neck-scale-vert-decr|incr",
        "head/head-scale-horiz-decr|incr",
    )
    def resolve(k):
        if k in e.mods and e.defs[k]: return k
        matches=[n for n in e.mods if n.startswith(k.split("-decr|incr")[0]+"-") and e.defs[n]]
        return matches[0] if len(matches)==1 else None
    selected=[x for k in names if (x:=resolve(k))]
    for group in ("buttocks","stomach","hip","pelvis","breast"):
        optional=next((k for k in regional if k.startswith(group+"/") and k not in selected),None)
        if optional: selected.append(optional)
    print("SELECTED",selected,flush=True)
    def conf(values, local=()):
        return dict(zip(global_names,values))|dict(zip(selected,local))
    paired=list(e.inventory()["product_controls"].items())
    equiv=[("neutral",{},{}),("current_waist",{next(k for k in e.mods if "/measure-waist-circ-" in k):-.4},{"waist":-.4}),
           ("current_combined",{next(k for k in e.mods if f"/measure-{s}-" in k):v for s,v in
              (("waist-circ",-.3),("hips-circ",.4),("shoulder-dist",.25))},{"waist":-.3,"hips":.4,"shoulder":.25})]
    for i,k in enumerate(global_names):
        equiv.append(("single_"+k.split("/")[-1],{k:.84 if i%2==0 else .19},{}))
    for k in selected[:4]:
        equiv.append(("regional_"+k.split("/")[-1],{k:-.45 if e.mods[k][0].getMin()<0 else .45},{}))
    genetics=[
       ("slim",conf([.10,.58,.73,.28,.39,.68,.30,.57],[.22,-.21,.15,.28])),
       ("muscular",conf([.91,.51,.49,.96,.74,.55,.48,.56],[.11,.25,-.11,.38])),
       ("high_mass",conf([.34,.74,.91,.44,.49,.29,.79,.22],[.31,.15,-.23,-.32])),
       ("adult_asymmetric",conf([.73,.64,.61,.67,.58,.37,.39,.65],[-.24,.13,.26,-.17])),
       ("extreme",conf([1,.95,.95,1,.93,.08,.86,.13],[.42,.35,.12,.21])),
    ]
    asym=next((k for k in e.mods if "l-upperarm-scale" in k and e.defs[k]),None)
    if asym: genetics[3][1][asym]=.35
    equiv += [(n,p,{}) for n,p in genetics]
    equiv += [("bare_regional",equiv[1][1],equiv[1][2])]
    records=[]
    for name,params,controls in equiv:
        nat, weights=e.native(params)
        exp=e.extended(params)
        actual=e.current(controls)
        reverse,_=e.native(params,reverse=True)
        regional_only_native=nat-e.native({})[0]+e.base
        row={"case":name,"config":params,"current_controls":controls,
              "C_vs_A_vertex_mm":summary(np.linalg.norm(exp-nat,axis=1)*100),
              "B_vs_A_vertex_mm":summary(np.linalg.norm(actual-nat,axis=1)*100),
              "B_vs_macro_subtracted_A_mm":summary(np.linalg.norm(actual-regional_only_native,axis=1)*100),
              "C_box_area_volume":metrics(exp*10,body_tri),"A_box_area_volume":metrics(nat*10,body_tri),
              "B_box_area_volume":metrics(actual*10,body_tri),
              "order_max_mm":float(np.max(np.linalg.norm(reverse-nat,axis=1))*100),"active_targets":len(weights)}
        if name in {"neutral","slim","muscular","high_mass","extreme"}:
            try: row["rig"]=native_rig(e,nat)
            except Exception as error:
                row["rig_error"]=repr(error)
        records.append(row)
        print("EQUIVALENCE",name,row["C_vs_A_vertex_mm"]["max"],row.get("rig_error"),flush=True)
    dump(out/"equivalence.json",records)
    dump(out/"configurations.json",dict(selected=selected,globals=global_names,profiles=dict(genetics)))

    rng=np.random.default_rng(626)
    train_ids=np.sort(rng.choice(e.skin,1400,replace=False))
    flat=(train_ids[:,None]*3+np.arange(3)).ravel()
    e.train_matrix=e.matrix[flat].tocsc()
    lo=np.array([e.mods[k][0].getMin() for k in global_names+selected])
    hi=np.ones(len(lo))
    priors=np.array([e.default[k] for k in global_names+selected])
    def extended(values,count,frozen=False,full=False):
        return e.extended(dict(zip(global_names+selected,values[:count])),frozen,
                          None if full else flat)
    def surface_eval(vertices,faces,ref,rt,levels,refprofile,refmask,center,scale):
        # Corresponding samples are shared for same-topology rows. Independent rows use different seeds.
        pred=sample(vertices,faces,12000,371)
        truth=sample(ref,rt,12000,371 if np.array_equal(faces,rt) else 372)
        d=cKDTree(truth).query(pred)[0]*10
        b=cKDTree(pred).query(truth)[0]*10
        pred_profile=measurements(vertices,faces,levels)
        reg={}
        for j,label in enumerate(("lower legs","upper legs","pelvis","torso","head and shoulder")):
            start=np.min(ref[:,1])+np.ptp(ref[:,1])*j/5
            stop=start+np.ptp(ref[:,1])/5
            r=np.r_[d[(pred[:,1]>=start)&(pred[:,1]<stop)],b[(truth[:,1]>=start)&(truth[:,1]<stop)]]
            if len(r): reg[label]=summary(r)
        ms=masks(vertices,faces,center,scale)
        ss=[dict(iou=float(np.sum(p&t)/max(1,np.sum(p|t))),
                false_positive_pixels=int(np.sum(p&~t)),false_negative_pixels=int(np.sum(t&~p))) for p,t in zip(ms,refmask)]
        mm=np.abs(pred_profile-refprofile)*10
        return dict(surface_mm=summary(np.r_[d,b]), regional_height_band_surface_mm=reg,
                 sections_error_mm=mm.tolist(), sections_cm=pred_profile.tolist(),silhouettes=ss,
                 geometry=metrics(vertices,faces))
    def fit(fn,x,lower,upper,ref,rt,kind,hier=False,initial=None):
        t=time.perf_counter()
        target_samples=sample(ref,rt,2700,710)
        tree=cKDTree(target_samples)
        target=ref[train_ids] if kind=="A" else None
        n=len(x)
        calls=0
        def residual(z):
            nonlocal calls
            calls+=1
            v=fn(z)*10
            if kind=="A":
                r=(v-target).ravel()
            else:
                ids=tree.query(v)[1]
                rid=cKDTree(v).query(target_samples[::3])[1]
                r=np.r_[(v-target_samples[ids]).ravel(),.8*(v[rid]-target_samples[::3]).ravel()]
            return np.r_[r, (z-x)*.12]
        kwargs=dict(max_nfev=22 if kind=="A" else 18,ftol=7e-5,gtol=2e-4,xtol=5e-5)
        if hier and n>len(global_names):
            g=len(global_names)
            first=least_squares(lambda z:residual(np.r_[z,x[g:]]),x[:g],
                               bounds=(lower[:g],upper[:g]),**kwargs)
            x0=np.r_[first.x,x[g:]]
            rpt=least_squares(lambda z:residual(np.r_[x0[:g],z]),x0[g:],
                             bounds=(lower[g:],upper[g:]),**kwargs)
            start=np.r_[x0[:g],rpt.x]
        else:
            start=x if initial is None else initial
        optimum=least_squares(residual,start,bounds=(lower,upper),**kwargs)
        return optimum.x,{"seconds":time.perf_counter()-t,"evaluations":calls,"status":int(optimum.status),
                          "objective":float(optimum.cost)}
    current_keys=[*dict(paired),*length_controls(e.body),*regional_controls(e.body)]
    eps=.10
    pos=np.stack([e.current({k:eps})-e.base for k in current_keys],axis=-1)/eps
    neg=np.stack([e.current({k:-eps})-e.base for k in current_keys],axis=-1)/eps
    def lin(z,base,p,n):
        return base+p@np.maximum(z,0)+n@np.maximum(-z,0)
    profiles=[]
    shape_payload={}
    def reference(case,kind,ref,rt,angles=None):
        print("FIT",case,flush=True)
        center=(ref.min(0)+ref.max(0))/2
        scale=153/np.ptp(ref[:,1])
        # Height-band profiles evaluated at fixed reference planes and a central torso crop.
        bbox=ref[np.unique(rt)]
        levels=bbox[:,1].min()+np.ptp(bbox[:,1])*np.linspace(.46,.79,12)
        refprofile=measurements(ref,rt,levels)
        refmask=masks(ref,rt,center,scale)
        rows=[]
        meshes={"reference":ref}
        def record(label,vertices,stats,config):
            v=vertices*10
            d=surface_eval(v,body_tri,ref,rt,levels,refprofile,refmask,center,scale)
            if kind=="A":
                d["corresponding_body_vertex_mm"]=summary(np.linalg.norm(v[e.skin]-ref[e.skin],axis=1)*10)
                jj=e.body["rig"]["joint_vertices"]
                d["landmark_error_mm"]=summary(np.array([np.linalg.norm(v[i].mean(0)-ref[i].mean(0))*10 for i in jj.values()]))
            if angles:
                joints=e.body["rig"]["joint_vertices"]
                refs={k:np.asarray(vals) for k,vals in angles.items() if vals is not None}
                errs={}
                for semantic,bone in {"shoulder.L":"upperarm01.L","shoulder.R":"upperarm01.R",
                                      "elbow.L":"lowerarm01.L","elbow.R":"lowerarm01.R",
                                      "hip.L":"upperleg01.L","hip.R":"upperleg01.R",
                                      "knee.L":"lowerleg01.L","knee.R":"lowerleg01.R"}.items():
                    anchor = semantic if semantic in refs else semantic.replace(".L","_l").replace(".R","_r")
                    if anchor in refs and refs[anchor].shape==(3,):
                        errs[semantic]=float(np.linalg.norm(v[joints[e.body["rig"]["bones"][bone]["head"]]].mean(0)-refs[anchor])*10)
                if errs: d["independent_semantic_landmark_error_mm"]=errs
            rows.append(dict(mode=label,**d,optimizer=stats,parameters=config))
            meshes[label]=v
            print("RESULT",case,label,d["surface_mm"]["mean"],flush=True)
        record("M0",e.base,{}, {})
        c,stat=fit(lambda z:lin(z,e.base[train_ids],pos[train_ids],neg[train_ids]),np.zeros(len(current_keys)),
                   np.full(len(current_keys),-.5),np.full(len(current_keys),.5),ref,rt,kind)
        record("M1",e.current(dict(zip(current_keys,c))),stat,dict(zip(current_keys,c)))
        for label,count,frozen in (("M2",len(global_names),False),("M3",len(priors),True),("M4",len(priors),False)):
            fn=lambda z: extended(z,count,frozen)
            c,stat=fit(fn,priors[:count],lo[:count],hi[:count],ref,rt,kind)
            if label=="M4":
                other,ost=fit(fn,priors[:count],lo[:count],hi[:count],ref,rt,kind,hier=True)
                stat["hierarchical"]=ost|{"parameters":dict(zip(global_names+selected,other))}
                choices=[("simultaneous",c,stat["objective"]),("hierarchical",other,ost["objective"])]
                stat["multistart"]=[]
                if kind=="A":
                    for endpoint in (.15,.85):
                        seed=priors.copy()
                        seed[0]=endpoint
                        seed[1]=.60
                        trial, report=fit(fn,priors[:count],lo[:count],hi[:count],ref,rt,kind,initial=seed)
                        stat["multistart"].append(report|{"gender_seed":endpoint})
                        choices.append((f"restart_{endpoint}",trial,report["objective"]))
                stat["selected"],c,stat["selected_objective"]=min(choices,key=lambda row:row[2])
                stat["total_strategy_seconds"]=stat["seconds"]+ost["seconds"]+sum(r["seconds"] for r in stat["multistart"])
            vv=extended(c,count,frozen,True)
            record(label,vv,stat,dict(zip(global_names+selected,c)))
        cbest=vv
        custom_names=[*length_controls(e.body),*regional_controls(e.body),"head_width","jaw_width"]
        p=np.stack([custom(e,cbest,{k:eps})-cbest for k in custom_names],axis=-1)/eps
        n=np.stack([custom(e,cbest,{k:-eps})-cbest for k in custom_names],axis=-1)/eps
        c,stat=fit(lambda z:lin(z,cbest[train_ids],p[train_ids],n[train_ids]),np.zeros(len(custom_names)),
                   np.full(len(custom_names),-.5),np.full(len(custom_names),.5),ref,rt,kind)
        extras=dict(zip(custom_names,c))
        record("M5",custom(e,cbest,extras),stat,extras)
        profiles.append(dict(case=case,family=kind,sections_y_cm=levels.tolist(),
                    reference_sections_cm=refprofile.tolist(),reference_metrics=metrics(ref,rt),rows=rows))
        dump(out/"capacity.json",profiles)
        if True:
            # Raw independently licensed reference stays local. Only the numeric map is exportable.
            v=meshes["M4"]
            samples=sample(ref,rt,24000,193)
            residual=cKDTree(samples).query(v)[0]*10
            np.savez_compressed(out/(case+".npz"),faces=body_tri,reference_faces=rt,
                                residual_mm=residual,**meshes)
    for name,params in genetics[:4]:
        reference("A_"+name,"A",e.native(params)[0]*10,body_tri)
    if args.independent:
        for sex,case in (("female","f_ca01"),("male","m_la01")):
            root=args.independent/f"MBLab_human_{sex}_{case}_bend0"
            data=(root/"mesh.json").read_bytes()
            man=json.loads((root/"manifest.json").read_text())
            assert hashlib.sha256(data).hexdigest()==man["mesh_sha256"]
            m=json.loads(data)
            raw=np.asarray(m["vertices"])
            native=e.base[e.skin]
            # Fixed one-time subject alignment. No candidate-specific transform or scale.
            scale=np.ptp(native[:,1])*10/np.ptp(raw[:,2])
            ref=np.c_[raw[:,0],raw[:,2]-raw[:,2].min(),-raw[:,1]]*scale
            ref[:,1]+=native[:,1].min()*10
            anchors={}
            for key,value in man["joint_anchors"].items():
                v=np.asarray(value)
                if v.shape==(3,):
                    anchors[key]=(np.array([v[0],v[2]-raw[:,2].min(),-v[1]])*scale+
                                  [0,native[:,1].min()*10,0]).tolist()
            dump(out/(f"B_{sex}_manifest.json"),dict(source=man["source_family"],identity=man["identity"],
                  sha256=man["mesh_sha256"],vertices=len(ref),scale_cm_per_m=float(scale),
                  vertical_origin_cm=float(native[:,1].min()*10),anchor_keys=list(anchors)))
            reference("B_"+sex,"B",ref,triangulate(m["faces"]),anchors)
    # Finite-difference sensitivity and observation conditioning. Width/depth use fixed planes.
    cm=e.extended({})*10
    levels=cm[e.skin,1].min()+np.ptp(cm[e.skin,1])*np.linspace(.46,.80,12)
    j=[]
    names=global_names+selected
    for k in names:
        x=e.default[k]
        lo_k=max(e.mods[k][0].getMin(),x-.025)
        hi_k=min(1,x+.025)
        a=e.extended({k:lo_k})*10
        b=e.extended({k:hi_k})*10
        j.append((measurements(b,body_tri,levels)-measurements(a,body_tri,levels))/(hi_k-lo_k))
    j=np.stack(j,axis=-1)
    controls={}
    for name,features in {"front":[0],"front_and_side":[0,1,2,3],"front_side_rear_proxy":[0,1,2,3],
                          "full_sections":[0,1,2,3,4]}.items():
        z=j[:,features,:].reshape(-1,len(names))
        singular=np.linalg.svd(z,compute_uv=False)
        controls[name]=dict(singular_values=singular.tolist(),rank_at_rel_1e_3=int(np.sum(singular>singular[0]*.001)))
    dump(out/"sensitivity.json",dict(names=names,planes_cm=levels.tolist(),columns=["width","depth","anterior","posterior","hull_perimeter"],
             derivatives_cm_per_unit=j.tolist(),observation_proxy_svd=controls))
    dump(out/"runtime.json",dict(seconds=time.perf_counter()-started,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None,
         cases=len(profiles), modes=sum(len(p["rows"]) for p in profiles)))

if __name__=="__main__":
    main()
