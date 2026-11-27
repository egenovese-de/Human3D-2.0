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
    # Regional refinement on held-out oracle residuals: identical basis and
    # bounded coefficient updates for every initialization. Not image fitting.
    from scipy.optimize import lsq_linear
    design=basis[:,ids,:].reshape(4,-1).T
    refinement=[]
    for name,weights in subjects:
        weights=np.asarray(weights)
        truth=base+np.tensordot(weights,basis,axes=1)
        proto=np.eye(4)[np.argmax(weights)]
        coarse=np.round(weights*4)/4; coarse/=coarse.sum()
        for method,start in {"neutral":np.zeros(4),"parametric":coarse,"prototype":proto,"hybrid":(proto+coarse)/2}.items():
            initial=base+np.tensordot(start,basis,axes=1)
            residual=(truth-initial)[ids].reshape(-1)
            result=lsq_linear(design,residual,bounds=(-.125,.125))
            final=base+np.tensordot(start+result.x,basis,axes=1)
            obj(name+"_"+method+"_refined",final)
            refinement.append({"subject":name,"method":method,"delta":result.x.tolist(),"solver_success":bool(result.success),**metrics(final,truth)})
    report={"refinement_scope":"bounded macro basis oracle residual; not regional or image fitting","refinement":refinement,"scope":"same-family oracle macro endpoint interpolation; not full MakeHuman modifier semantics; no independent geometry","source_revision":"e0ae4eae57347466b5757bbcdaaa7194bdd31c94","asset_revision":manifest["revision"],"subjects":subjects,"rows":rows,"vertices":len(base),"body_vertices":len(ids),"asset_hashes":{k:v["sha256"] for k,v in entries.items() if k.endswith("base.obj") or any(k.endswith(f"{p}-{s}-{a}.target") for p in ("african","asian","caucasian") for s in ("female","male") for a in ("young","old"))}}
    # Expanded adult basis: universal weight/muscle endpoints relative to
    # average, plus admitted torso pairs. Same-family additive oracle only.
    def dense(rel,group="foundation"):
        if group=="foundation": raw=read(rel)
        else:
            manifest2=json.loads((ROOT/"lab/manifests/makehuman-anatomical-torso.json").read_text())
            e=next(x for x in manifest2["files"] if x["path"]==rel)
            p=runtime/"assets"/group/(manifest2.get("source_prefix","")+rel)
            if digest(p)!=e["sha256"]: raise ValueError(rel)
            raw=p.read_text()
        v=np.zeros_like(base)
        seen=set()
        for line in raw.splitlines():
            line=line.partition("#")[0].strip()
            if not line: continue
            i,x,y,z=line.split(); i=int(i)
            if not 0<=i<len(base) or i in seen: raise ValueError("invalid target index")
            seen.add(i); v[i]=[float(x),float(y),float(z)]
        if not np.isfinite(v).all(): raise ValueError("nonfinite target")
        return v
    expanded=[]
    for name,weights in subjects:
        form="female" if sum(weights[:2])>sum(weights[2:]) else "male"
        prefix="data/targets/macrodetails/universal-"+form+"-young-"
        avg=dense(prefix+"averagemuscle-averageweight.target")
        fields=[dense(prefix+"averagemuscle-maxweight.target")-avg,dense(prefix+"maxmuscle-averageweight.target")-avg]
        tm=json.loads((ROOT/"lab/manifests/makehuman-anatomical-torso.json").read_text())
        for stem in ("torso-scale-depth","torso-scale-horiz","torso-vshape"):
            rel=next(x["path"] for x in tm["files"] if x["path"].endswith(stem+"-incr.target"))
            fields.append(dense(rel,"anatomical_torso"))
        fields=np.asarray(fields)
        coeff=np.array([.65,.35,.30,.20,.15]) if name in ("dev01","hold02") else np.array([.25,.70,.15,.35,.25])
        macro=base+np.tensordot(weights,basis,axes=1)
        truth=macro+avg+np.tensordot(coeff,fields,axes=1)
        coarse=np.round(coeff*4)/4
        candidates={"macro_only":macro+avg,"weight_muscle":macro+avg+np.tensordot(coarse[:2],fields[:2],axes=1),"expanded":macro+avg+np.tensordot(coarse,fields,axes=1)}
        obj(name+"_expanded_truth",truth)
        for method,v in candidates.items():
            obj(name+"_"+method+"_expanded",v)
            expanded.append({"subject":name,"method":method,"coefficients":coeff.tolist(),**metrics(v,truth)})
    report["expanded_scope"]="same-family additive adult weight/muscle and torso oracle; not upstream modifier equivalence"
    report["expanded"]=expanded
    # Validate all generated body meshes against the neutral connectivity.
    tri=np.asarray([[f[0],f[k],f[k+1]] for f in body_faces for k in range(1,len(f)-1)])
    def area(v):
        a,b,c=v[tri[:,0]],v[tri[:,1]],v[tri[:,2]]
        return np.linalg.norm(np.cross(b-a,c-a),axis=1)/2
    reference=area(base); stable=reference>1e-10
    integrity=[]
    for p in sorted(out.glob("*.obj")):
        v=np.asarray([[float(x) for x in line.split()[1:]] for line in p.read_text().splitlines() if line.startswith("v ")])
        a=area(v); ratio=a[stable]/reference[stable]
        finite=bool(np.isfinite(v).all())
        integrity.append({"mesh":p.name,"finite":finite,"vertices":len(v),"triangles":len(tri),"collapsed_stable_faces":int(np.sum(a[stable]<=1e-10)),"area_ratio_min":float(ratio.min()),"area_ratio_max":float(ratio.max()),"sha256":digest(p)})
        if not finite or len(v)!=len(base): raise ValueError("invalid mesh")
    report["integrity"]=integrity
    (out/"metrics.json").write_text(json.dumps(report,indent=2))
    print("X_P1="+json.dumps(report))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();main(a.runtime,a.output)
