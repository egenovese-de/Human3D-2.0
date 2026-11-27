"""Compare 8+5, 8+10 and 8+19 regional budgets with common starts and data."""
import json
import sys
from pathlib import Path
import time
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from g1_benchmark import Engine, dump, sample

def main(root):
    e=Engine()
    cfg=json.loads((root/"configurations.json").read_text())
    g=cfg["globals"]; local=cfg["selected"]
    order=("torso/torso-scale-depth","measure/measure-shoulder-dist","measure/measure-hips-circ",
           "measure/measure-waist-circ","measure/measure-thigh-circ","measure/measure-bust-circ",
           "measure/measure-upperarm-circ","measure/measure-calf-circ","hip/hip-scale-depth","buttocks/buttocks-volume")
    local=sorted(local,key=lambda k:next((i for i,s in enumerate(order) if k.startswith(s)),len(order)))
    indices=np.sort(np.random.default_rng(626).choice(e.skin,1400,replace=False))
    flat=(indices[:,None]*3+np.arange(3)).ravel()
    e.train_matrix=e.matrix[flat].tocsc()
    rows=[]
    for path in sorted(root.glob("*.npz")):
        with np.load(path) as a:
            ref=a['reference']; rt=a['reference_faces']; tri=a['faces']
        family=path.stem[0]
        train=sample(ref,rt,2700,710)
        model=cKDTree(train)
        ev=sample(ref,rt,12000,912)
        ev_tree=cKDTree(ev)
        case=[]
        for n in (5,10,len(local)):
            t=time.perf_counter()
            names=g+local[:n]
            priors=np.array([e.default[k] for k in names])
            lo=np.array([e.mods[k][0].getMin() for k in names]); hi=np.ones(len(lo))
            def res(params):
                points=e.extended(dict(zip(names,params)),vertices=flat)*10
                if family=='A':
                    delta=(points-ref[indices]).ravel()
                else:
                    i=model.query(points)[1]; j=cKDTree(points).query(train[::3])[1]
                    delta=np.r_[(points-train[i]).ravel(),.8*(points[j]-train[::3]).ravel()]
                return np.r_[delta,(params-priors)*.12]
            starts=[priors,priors.copy(),priors.copy()]
            starts[1][0]=.15; starts[2][0]=.85
            opts=[least_squares(res,x,bounds=(lo,hi),max_nfev=18,ftol=7e-5,gtol=2e-4,xtol=5e-5) for x in starts]
            opt=min(opts,key=lambda x:x.cost)
            shape=e.extended(dict(zip(names,opt.x)))*10
            pts=sample(shape,tri,12000,913)
            test=float(np.r_[ev_tree.query(pts)[0],cKDTree(pts).query(ev)[0]].mean()*10)
            case.append(dict(regional_count=n,objective=float(opt.cost),point_to_point_mm=test,
                corresponding_vertex_rmse_mm=float(np.sqrt(np.mean(np.sum((shape[e.skin]-ref[e.skin])**2,axis=1)))*10) if family=='A' else None,
                seconds=time.perf_counter()-t))
        rows.append({"case":path.stem,"rows":case})
        print(path.stem,[round(r['point_to_point_mm'],3) for r in case],flush=True)
    dump(root/"basis_ablation.json",dict(selection_order=local,rows=rows))
if __name__=="__main__":main(Path(sys.argv[1]))
