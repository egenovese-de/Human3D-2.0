"""Macro/region sweeps, dependency ablation, and off-basis residual probe."""
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.spatial import cKDTree
from g1_benchmark import Engine, triangulate, dump, summary, sample, measurements, metrics

def main(root):
    e=Engine()
    configs=json.loads((root/"configurations.json").read_text())
    tri=triangulate(e.faces)
    profiles={"native_default":{},**configs["profiles"]}
    globals_=configs["globals"]
    local=configs["selected"]
    e.rig_path=Path(__import__("os").environ["U"])/"data/rigs/default.mhskel"
    geometric={}
    rows=[]
    for name,controls in profiles.items():
        q=e.extended(controls)
        points=q*10
        bbox=points[e.skin]
        y=bbox[:,1].min()+np.ptp(bbox[:,1])*np.linspace(.45,.79,12)
        base=measurements(points,tri,y)
        geometric[name]={"geometry":metrics(points,tri),"section_centimetres":base.tolist(),"plane_centimetres":y.tolist()}
        for k in globals_+local:
            m=e.mods[k][0]
            if m.isMacro():
                low,high=(.49,.91) if m.name=="Age" else (.10,.90)
            else:
                low,high=(max(m.getMin(),-.65),.65)
            p=e.extended(controls|{k:low})
            r=e.extended(controls|{k:high})
            effect=(r-p)[e.skin]*100/(high-low)
            active=np.linalg.norm(effect,axis=1)
            # Independent native dependency changes show up in cross-profile shape and scale.
            rows.append({"profile":name,"parameter":k,"low":low,"high":high,
                         "effect_mm_per_unit":summary(active),
                         "max_height_delta_cm":float(abs(np.ptp(r[e.skin,1])-np.ptp(p[e.skin,1]))*10),
                         "section_delta_cm":(measurements(r*10,tri,y)-measurements(p*10,tri,y)).tolist()})
    dump(root/"modifier_sweeps.json",dict(profiles=geometric,rows=rows))
    result=[]
    cases=json.loads((root/"capacity.json").read_text())
    excludes={"genitals","bodyshapes"}
    fields=[k for k,(mod,_) in e.mods.items() if not mod.isMacro() and mod.groupName not in excludes and e.defs[k]]
    for c in cases:
        model=next(row for row in c["rows"] if row["mode"]=="M4")["parameters"]
        t=time.monotonic()
        with np.load(root/(c["case"]+".npz")) as case:
            ref=case["reference"]/10; rt=case["reference_faces"]
            v=case["M4"]/10
        train=np.sort(np.random.default_rng(92).choice(e.skin,1400,replace=False))
        held=sample(ref,rt,15000,2421)
        tree=cKDTree(sample(ref,rt,5000,951))
        def target(q):
            if c["family"]=="A": return ref[train]-q[train]
            return tree.data[tree.query(q[train])[1]]-q[train]
        residual=target(v)
        candidates=[]
        for name in fields:
            key=e.mods[name][0]
            current=model.get(name,e.default[name])
            for direction in (-1,1):
                step=direction*min(.25,1-current if direction>0 else current-key.getMin())
                if abs(step)<1e-7: continue
                p=e.extended(model|{name:current+step})
                field=(p-v)[train]
                den=np.sum(field**2)+.05
                a=float(np.clip(np.sum(field*residual)/den,0,1))
                predicted=float(2*a*np.sum(field*residual)-a*a*den)
                candidates.append((predicted,name,step,field))
        candidates.sort(key=lambda x:x[0],reverse=True)
        active={}
        for _ in range(2):
            for _,name,step,field in candidates[:36]:
                if name in active: continue
                alpha=float(np.clip(np.sum(field*residual)/(np.sum(field**2)+.05),0,1))
                if alpha>.015:
                    active[name]=model.get(name,e.default[name])+alpha*step
                    residual-=alpha*field
        print(c["case"],len(candidates),len(active),flush=True)
        def dist(points):
            observed=sample(points,tri,15000,133)
            return summary(np.r_[cKDTree(held).query(observed)[0],cKDTree(observed).query(held)[0]]*100)
        new=e.extended(model|active)
        result.append(dict(case=c["case"],tested_endpoints=len(candidates),shortlist=36,
                 baseline=dist(v),expanded=dist(new),extra_controls=active,
                 selected_correspondence_mm=summary(np.linalg.norm(new[e.skin]-ref[e.skin],axis=1)*100) if c["family"]=="A" else None,
                 seconds=time.monotonic()-t))
        dump(root/"expanded_regional_probe.json",result)
if __name__=="__main__":
    main(Path(sys.argv[1]))
