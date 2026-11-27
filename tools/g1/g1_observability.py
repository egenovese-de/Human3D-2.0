"""Controlled calibrated-view conditioning and local identifiability."""
from pathlib import Path
import argparse
import json
import numpy as np
from scipy.optimize import lsq_linear
from g1_benchmark import Engine, triangulate, dump

def cuts(vertices,triangles,y):
    f=vertices[triangles]
    result=[]
    for a,b in ((0,1),(1,2),(2,0)):
        p,q=f[:,a], f[:,b]
        usable=(p[:,1]>y)!=(q[:,1]>y)
        p,q=p[usable],q[usable]
        return_line=p+(q-p)*((y-p[:,1])/(q[:,1]-p[:,1]))[:,None]
        result.append(return_line[:,[0,2]])
    return np.concatenate(result)

def vector(points,tri,levels,angles):
    directions=np.array([(np.cos(np.deg2rad(a)),-np.sin(np.deg2rad(a))) for a in angles])
    rows=[]
    for y in levels:
        x=cuts(points,tri,y)
        basis=x@directions.T
        rows.append(np.stack([basis.min(0),basis.max(0)],axis=-1))
    return np.array(rows).transpose(1,0,2)

def properties(e,v):
    v=v*10
    j={k:v[idx].mean(0) for k,idx in e.body["rig"]["joint_vertices"].items()}
    bones=e.body["rig"]["bones"]
    vbody=v[e.skin]
    return {"standing_extent_cm":float(np.ptp(vbody[:,1])),
            "bone_lengths_cm":{name:float(np.linalg.norm(j[bones[name]["head"]]-j[bones[name]["tail"]]))
                               for name in ("upperarm01.L","lowerarm01.L","upperleg01.L","lowerleg01.L","spine02","neck01")
                               if name in bones},
            "joint_centers_cm":{name:j[name].tolist() for name in j},
            "shoulder_joint_span_cm":float(np.linalg.norm(j[bones["upperarm01.L"]["head"]]-j[bones["upperarm01.R"]["head"]]))}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--configs",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    e=Engine()
    cfg=json.loads(a.configs.read_text())
    names=cfg["globals"]+cfg["selected"]
    all_angles=(0,90,180,45,135)
    xyz=e.extended({})*10
    tri=triangulate(e.faces)
    low,high=xyz[e.skin,1].min(),xyz[e.skin,1].max()
    levels=low+(high-low)*np.linspace(.42,.78,14)
    indices=np.linspace(0,len(e.skin)-1,1200,dtype=int)
    vertices=e.skin[indices]
    rows={}
    rng=np.random.default_rng(172)
    for label,profile in {"default":{}, "slim":cfg["profiles"]["slim"], "high_mass":cfg["profiles"]["high_mass"]}.items():
        initial=np.array([profile.get(k,e.default[k]) for k in names])
        rest=e.extended(profile)*10
        neutral=vector(rest,tri,levels,all_angles)
        rng_delta=rng.uniform(-.075,.075,len(names))
        lower=np.array([e.mods[k][0].getMin() for k in names])-initial
        upper=1-initial
        fitted_delta=np.clip(rng_delta,lower,upper)
        truth=e.extended(dict(zip(names,initial+fitted_delta)))*10
        truth_obs=vector(truth,tri,levels,all_angles)
        matrix=[]; geom=[]
        for i,k in enumerate(names):
            minus=max(e.mods[k][0].getMin(),initial[i]-.015)
            plus=min(1,initial[i]+.015)
            l=e.extended(profile|{k:minus})*10
            r=e.extended(profile|{k:plus})*10
            matrix.append((vector(r,tri,levels,all_angles)-vector(l,tri,levels,all_angles))/(plus-minus))
            geom.append(((r[vertices]-l[vertices])/(plus-minus)).ravel())
        matrix=np.stack(matrix,axis=-1)
        full=np.stack(geom,axis=-1)
        features={}
        for key, views in {"front":[0],"front_side":[0,1],"front_side_rear":[0,1,2],
                          "oblique_multiview":[0,1,3,4],"complete_3d":None}.items():
            if views is None:
                j=full
                residual=(truth[vertices]-rest[vertices]).ravel()
            else:
                j=matrix[views].reshape(-1,len(names))
                residual=(truth_obs[views]-neutral[views]).ravel()
            singular=np.linalg.svd(j,compute_uv=False)
            norm=np.linalg.norm(j,axis=0)
            j_normal=j/np.maximum(norm,1e-12)
            cosine=j_normal.T@j_normal
            valid=np.triu(np.abs(cosine),1)
            pair=np.unravel_index(np.argmax(valid),valid.shape)
            for_nuisance=None
            if views is not None:
                scale_vector=neutral[views].ravel()
                center_vector=np.tile([1.,1.], len(scale_vector)//2)
                nuisance=np.stack([scale_vector,center_vector],axis=-1)
                q=np.linalg.qr(nuisance)[0]
                jw=j-q@(q.T@j)
                sval=np.linalg.svd(jw,compute_uv=False)
                for_nuisance=int(np.sum(sval>sval[0]*.001))
            reg=.18
            dx=lsq_linear(np.vstack([j,reg*np.eye(len(names))]),np.r_[residual,np.zeros(len(names))],
                          bounds=(lower,upper),max_iter=100).x
            estimate=e.extended(dict(zip(names,initial+dx)))*10
            features[key]={"rank_rel_1e_3":int(np.sum(singular>singular[0]*.001)),
                           "rank_after_scale_xshift_projection":for_nuisance,
                           "singular_values":singular.tolist(),"column_norm":norm.tolist(),
                           "most_correlated_pair":[names[i] for i in pair],"absolute_cosine":float(valid[pair]),
                           "local_inverse_parameter_mae":float(np.mean(np.abs(dx-fitted_delta))),
                           "local_inverse_surface_rmse_mm":float(np.sqrt(np.mean(np.sum((estimate[e.skin]-truth[e.skin])**2,1)))*10)}
        rows[label]={"measurements":properties(e,rest/10),"rank_and_inverse":features,"section_jacobian":matrix.tolist()}
        print(label,[(k,r["rank_rel_1e_3"],round(r["local_inverse_surface_rmse_mm"],2)) for k,r in features.items()],flush=True)
    dump(a.output,dict(parameters=names,angles=list(all_angles),planes_cm=levels.tolist(),
                       observation="calibrated orthographic exact section extrema; noiseless; same native stance",
                       experiment=rows))

if __name__=="__main__":
    main()
