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
    from human3d.bootstrap import _rig
    from human3d.native_rig import validate_rebind, pose_transforms, skin_vertices, validate_pose
    from human3d.alignment import Camera, Alignment
    rig=_rig(json.loads(read("data/rigs/default.mhskel")),json.loads(read("data/rigs/default_weights.mhw")),mesh["vertices"])
    body={"mesh":mesh,"rig":rig,"morph_targets":{}}
    checks=[]
    # Preserve source UV mapping; OBJ pilot files themselves omit UV and rig.
    uv_count=len(mesh["texcoords"])
    for f in mesh["faces"]:
        for i,u in f["corners"]:
            if not 0<=i<len(base) or not 0<=u<uv_count: raise ValueError("invalid UV or vertex index")
    for p in sorted(out.glob("*expanded*.obj")):
        v=np.asarray([[float(x) for x in line.split()[1:]] for line in p.read_text().splitlines() if line.startswith("v ")])
        row={"mesh":p.name,"uv_source_count":uv_count,"bones":len(rig["bones"])}
        try:
            joints=validate_rebind(body,v)
            t=pose_transforms(rig,joints,Alignment(Camera(0,200/np.ptp(base[:,1]),0j,1),0,{"lowerarm01.L":.15}))
            posed=np.asarray(skin_vertices(v,rig["skin"],t))
            validate_pose(body,v,posed)
            if np.max(np.abs(posed-v))<=1e-6: raise ValueError("pose_no_effect")
            row.update(status="PASS",pose_delta=float(np.max(np.abs(posed-v))))
        except Exception as exc:
            row.update(status="FAIL",reason=str(exc))
        checks.append(row)
    report["rig_uv"]=checks
    diagnostics=[]
    stable_native=reference>5e-7
    for p in sorted(out.glob("*expanded*.obj")):
        v=np.asarray([[float(x) for x in line.split()[1:]] for line in p.read_text().splitlines() if line.startswith("v ")])
        a=area(v)
        ratio=np.divide(a,reference,out=np.ones_like(a),where=stable_native)
        bad=np.flatnonzero(stable_native & ((ratio<.03)|(ratio>30)))
        row={"mesh":p.name,"outlier_count":len(bad),"outliers":[]}
        for i in bad:
            ids=tri[i]
            influences={}
            for j in ids:
                for bone,w in rig["skin"][j].items(): influences[bone]=influences.get(bone,0)+w/3
            row["outliers"].append({"triangle":int(i),"vertices":ids.tolist(),"center":base[ids].mean(axis=0).tolist(),"ratio":float(ratio[i]),"dominant_bone":max(influences,key=influences.get) if influences else None})
        if len(bad):
            # Diagnostic only: minimal global retreat towards neutral, no gate relaxation.
            lo,hi=0.,1.
            for _ in range(24):
                mid=(lo+hi)/2
                try: validate_rebind(body,base+mid*(v-base));lo=mid
                except ValueError: hi=mid
            repaired=base+lo*(v-base)
            validate_rebind(body,repaired)
            row["retained_deformation_fraction"]=lo
            row["repair_mean_displacement_mm"]=float(np.linalg.norm((repaired-v)[np.unique(tri)],axis=1).mean()*100)
        diagnostics.append(row)
    report["distortion_diagnostics"]=diagnostics
    repairs=[]
    for row in diagnostics:
        if not row["outlier_count"]: continue
        p=out/row["mesh"]
        v=np.asarray([[float(x) for x in line.split()[1:]] for line in p.read_text().splitlines() if line.startswith("v ")])
        seed=set(i for item in row["outliers"] for i in item["vertices"])
        result={"mesh":p.name,"status":"FAIL"}
        for rings in range(5):
            ids=np.array(sorted(seed))
            for alpha in np.linspace(.05,1,20):
                fixed=v.copy();fixed[ids]+=alpha*(base[ids]-v[ids])
                try:
                    joints=validate_rebind(body,fixed)
                    t=pose_transforms(rig,joints,Alignment(Camera(0,200/np.ptp(base[:,1]),0j,1),0,{"lowerarm01.L":.15}))
                    posed=np.asarray(skin_vertices(fixed,rig["skin"],t))
                    validate_pose(body,fixed,posed)
                    if np.max(np.abs(posed-fixed))<=1e-6: raise ValueError("pose_no_effect")
                except ValueError: continue
                shift=np.linalg.norm(fixed-v,axis=1)*100
                result.update(status="PASS",rings=rings,alpha=float(alpha),changed_vertices=int(np.count_nonzero(shift>1e-8)),mean_shift_mm=float(shift[np.unique(tri)].mean()),max_shift_mm=float(shift.max()),pose_delta=float(np.max(np.abs(posed-fixed))))
                obj(p.stem+"_local_repair",fixed)
                break
            if result["status"]=="PASS": break
            previous=seed.copy()
            seed.update(int(i) for face in tri if any(int(j) in previous for j in face) for i in face)
        repairs.append(result)
    report["local_repairs"]=repairs
    # Persist the validated anatomy, with original topology, UV and rebound joints.
    from copy import deepcopy
    from types import SimpleNamespace
    from human3d.frozen_body import load_frozen_body
    from human3d.usd_export import export_body
    from pxr import Usd, UsdGeom, UsdSkel
    from PIL import Image
    persist=out/"assets";persist.mkdir()
    persistence=[]
    body_ids=np.unique(tri)
    for name,_ in subjects:
        path=out/(name+"_expanded_expanded.obj")
        repaired=out/(path.stem+"_local_repair.obj")
        if repaired.exists(): path=repaired
        v=np.asarray([[float(x) for x in line.split()[1:]] for line in path.read_text().splitlines() if line.startswith("v ")])
        joints=validate_rebind(body,v)
        frozen=deepcopy(body)
        frozen.update(schema_version=1,kind="frozen_body")
        frozen["mesh"]["vertices"]=v.tolist()
        frozen["rig"]["joints"]={k:a.tolist() for k,a in joints.items()}
        raw=json.dumps(frozen,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        fp=persist/(hashlib.sha256(raw).hexdigest()+".json");fp.write_bytes(raw)
        restored=load_frozen_body(fp)
        if json.dumps(restored,sort_keys=True,separators=(",",":"),allow_nan=False).encode()!=raw: raise ValueError("frozen roundtrip mismatch")
        dst=persist/(name+".usdz")
        alignment=Alignment(Camera(0,200/np.ptp(base[:,1]),0j,1),0,{})
        export_body(dst,restored,SimpleNamespace(controls={}),alignment,texture=Image.new("RGB",(32,32),(180,180,180)))
        stage=Usd.Stage.Open(str(dst))
        m=UsdGeom.Mesh.Get(stage,"/Human/Body")
        uv=UsdGeom.PrimvarsAPI(m).GetPrimvar("st")
        sk=UsdSkel.Skeleton.Get(stage,"/Human/Rig")
        binding=UsdSkel.BindingAPI(m.GetPrim())
        weights=np.asarray(binding.GetJointWeightsPrimvar().Get()).reshape(len(body_ids),-1)
        err=float(np.max(np.abs(np.asarray(m.GetPointsAttr().Get())-v[body_ids])))
        if err>1e-5 or len(sk.GetJointsAttr().Get())!=len(rig["bones"]) or len(uv.GetIndices())!=sum(len(f) for f in body_faces) or not np.allclose(weights.sum(axis=1),1,atol=1e-6): raise ValueError("USD persistence mismatch")
        persistence.append({"subject":name,"status":"PASS","frozen_sha256":digest(fp),"usdz_sha256":digest(dst),"vertices":len(body_ids),"bones":len(sk.GetJointsAttr().Get()),"uv_corners":len(uv.GetIndices()),"point_max_error_mm":err*100})
    report["persistence"]=persistence
    # Independent deformation generator, not independent topology or human scan.
    # Smooth spatial warps are not synthesized from any MakeHuman target basis.
    independent=[]
    y=base[:,1];x=base[:,0];z=base[:,2]
    for name,amp in (("warp01",.12),("warp02",-.10),("warp03",.18),("warp04",-.16)):
        truth=base.copy()
        truth[:,0]+=amp*x*np.exp(-((y-1.2)/2.3)**2)
        truth[:,2]+=amp*2*np.exp(-((y-.2)/1.8)**2-(x/2.2)**2)
        truth[:,1]+=amp*.6*np.tanh(y/3)
        validate_rebind(body,truth)
        obj(name+"_truth",truth)
        # Identical oracle surface observations, disjoint sampled and evaluation vertices.
        train=body_ids[::3];test=np.setdiff1d(body_ids,train)
        D=basis[:,train,:].reshape(4,-1).T
        result=lsq_linear(D,(truth-base)[train].reshape(-1),bounds=(0,1))
        pred=base+np.tensordot(result.x,basis,axes=1)
        for method,v in (("neutral",base),("parametric",pred)):
            obj(name+"_"+method,v)
            dist=np.linalg.norm(v[test]-truth[test],axis=1)*100
            independent.append({"subject":name,"method":method,"mean_mm":float(dist.mean()),"p95_mm":float(np.percentile(dist,95)),"train_vertices":len(train),"test_vertices":len(test)})
    report["independent_deformation_scope"]="procedural spatial warp, shared MakeHuman topology, oracle 3D observations; not independent human scan or image reconstruction"
    report["independent_deformation"]=independent
    from x_p1_regions import benchmark
    regional_fields = []
    for stem in ("torso-scale-depth", "torso-scale-horiz", "torso-vshape"):
        rel = next(e["path"] for e in tm["files"] if e["path"].endswith(stem + "-incr.target"))
        regional_fields.append(dense(rel, "anatomical_torso"))
    regional_manifest = json.loads((ROOT / "lab/manifests/makehuman-p1-anatomy.json").read_text())
    for entry in regional_manifest["files"]:
        rel = entry["path"]
        if "-incr.target" in rel:
            path = runtime / "assets/p1_anatomy" / rel
            if digest(path) != entry["sha256"]:
                raise ValueError(f"Invalid regional target: {rel}")
            field = np.zeros_like(base)
            for line in path.read_text().splitlines():
                line = line.partition("#")[0].strip()
                if line:
                    i, *delta = line.split()
                    index = int(i)
                    if not 0 <= index < len(base):
                        raise ValueError(f"Invalid target index: {rel}")
                    field[index] = [float(value) for value in delta]
            if "/l-" in rel:
                from scipy.spatial import cKDTree
                reflection = np.array([-1, 1, 1])
                mirrored = cKDTree(base).query(base * reflection)[1]
                field += field[mirrored] * reflection
            regional_fields.append(field)
    report["regional_experiment"] = benchmark(base, tri, basis, np.asarray(regional_fields), body, out / "regional")
    regional = report["regional_experiment"]
    (out / "regional" / "metrics.json").write_text(json.dumps(regional, indent=2, allow_nan=False))
    (out/"metrics.json").write_text(json.dumps(report,indent=2))
    print("X_P1="+json.dumps({k: v for k, v in report.items() if k != "regional_experiment"}))
    print("X_P1_REGIONAL_COMPLETE", len(regional["rows"]))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();main(a.runtime,a.output)
