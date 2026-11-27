"""P1 same-family oracle control, not independent anatomy qualification."""
import argparse, json, hashlib
from pathlib import Path
import numpy as np
from human3d.bootstrap import _mesh, _morph_targets
from bootstrap import ROOT, digest

def main(runtime,out):
    out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((ROOT/"DOCS/manifests/makehuman-v1.3.0.json").read_text())
    entries={x["path"]:x for x in manifest["files"]}
    def read(rel):
        e=entries[rel]; p=runtime/"assets/foundation"/manifest["source_prefix"]/rel
        if digest(p)!=e["sha256"]: raise ValueError(rel)
        return p.read_text()
    mesh=_mesh(read("data/3dobjs/base.obj"))
    base=np.asarray(mesh["vertices"],dtype=float)
    # Adult macro endpoints, averaged across the three upstream population bases.
    # These are geometry basis controls, not inferred ethnicity.
    basis=[]
    for form in ("female","male"):
        for age in ("young","old"):
            ds=[]
            for prefix in ("african","asian","caucasian"):
                rel=f"data/targets/macrodetails/{prefix}-{form}-{age}.target"
                d=np.zeros_like(base)
                for line in read(rel).splitlines():
                    line=line.partition('#')[0].strip()
                    if not line: continue
                    i,x,y,z=line.split()
                    i=int(i)
                    if not 0<=i<len(base): raise ValueError('target index out of range')
                    d[i]=[float(x),float(y),float(z)]
                if not np.isfinite(d).all(): raise ValueError('nonfinite target')
                ds.append(d)
            basis.append(np.mean(ds,axis=0))
    basis=np.asarray(basis)
    body_faces=[[i for i,_ in f["corners"]] for f in mesh["faces"] if f["group"]=="body"]
    ids=np.unique(np.concatenate(body_faces))
    def obj(name,v):
        with (out/(name+".obj")).open("w") as f:
            for x,y,z in v: f.write(f"v {x:.9g} {y:.9g} {z:.9g}\n")
            for face in body_faces: f.write("f "+" ".join(str(i+1) for i in face)+"\n")
    def metrics(v,t):
        d=np.linalg.norm(v[ids]-t[ids],axis=1)*100 # MakeHuman decimetres to mm
        return {"mean_mm":float(d.mean()),"p95_mm":float(np.percentile(d,95)),"finite":bool(np.isfinite(v).all())}
    # Explicit same-family oracle mixtures; no fitted labels or image inference.
    subjects=[("dev01",[.8,.1,.1,0]),("dev02",[.1,0,.8,.1]),("hold01",[.15,.65,.05,.15]),("hold02",[.05,.15,.25,.55])]
    rows=[]
    for name,w in subjects:
        w=np.asarray(w); truth=base+np.tensordot(w,basis,axes=1)
        proto=np.eye(4)[np.argmax(w)]
        # Parametric uses coarse quantized oracle coefficients; hybrid uses same
        # information budget with residual interpolation. No claim of superiority.
        coarse=np.round(w*4)/4; coarse/=coarse.sum()
        hybrid=(proto+coarse)/2
        candidates={"neutral":base,"parametric":base+np.tensordot(coarse,basis,axes=1),"prototype":base+np.tensordot(proto,basis,axes=1),"hybrid":base+np.tensordot(hybrid,basis,axes=1)}
        obj(name+"_truth",truth)
        for method,v in candidates.items():
            obj(name+"_"+method,v)
            rows.append({"subject":name,"method":method,**metrics(v,truth)})
    report={"scope":"same-family oracle macro endpoint interpolation; not full MakeHuman modifier semantics; no independent geometry","source_revision":"e0ae4eae57347466b5757bbcdaaa7194bdd31c94","asset_revision":manifest["revision"],"subjects":subjects,"rows":rows,"vertices":len(base),"body_vertices":len(ids),"asset_hashes":{k:v["sha256"] for k,v in entries.items() if k.endswith("base.obj") or any(k.endswith(f"{p}-{s}-{a}.target") for p in ("african","asian","caucasian") for s in ("female","male") for a in ("young","old"))}}
    (out/"metrics.json").write_text(json.dumps(report,indent=2))
    print("X_P1="+json.dumps(report))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();main(a.runtime,a.output)
