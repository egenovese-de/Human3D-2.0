"""Known-geometry CC0 control; no photographic or GPT inference claim."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw
from human3d.bootstrap import ASSETS, MORPH_ASSETS, _mesh, _rig, _morph_targets
from human3d.frozen_body import deform_vertices
from human3d.alignment import Camera, Alignment
from human3d.fitting import fit_body
from human3d.native_rig import validate_rebind, pose_transforms, skin_vertices, validate_pose
from human3d.usd_export import export_body

def main(runtime, out):
    def read(name, expected):
        matches=[p for p in (runtime/"assets").rglob(name) if p.is_file()]
        valid=[p.read_bytes() for p in matches if hashlib.sha256(p.read_bytes()).hexdigest()==expected]
        if not valid: raise ValueError("missing or corrupt asset "+name)
        return valid[0]
    a={n:read(n,h) for n,h in ASSETS.items()}
    mesh=_mesh(a["base.obj"].decode())
    rig=_rig(json.loads(a["default.mhskel"]),json.loads(a["default_weights.mhw"]),mesh["vertices"])
    morphs=_morph_targets({n:read(n,h) for n,h in MORPH_ASSETS.items()},len(mesh["vertices"]))
    body={"mesh":mesh,"rig":rig,"morph_targets":morphs}
    rest=np.asarray(deform_vertices(body,{}))
    truth=np.asarray(deform_vertices(body,{"hips":.5}))
    assert np.max(np.abs(truth-rest))>0
    assert np.array_equal(truth,np.asarray(deform_vertices(body,{"hips":.5})))
    camera=Camera(0,200/np.ptp(rest[:,1]),complex(128,128+200/np.ptp(rest[:,1])*float((rest[:,1].min()+rest[:,1].max())/2)),1)
    alignment=Alignment(camera,0,{})
    image=Image.new("1",(256,256))
    draw=ImageDraw.Draw(image)
    points=[camera.project(v) for v in truth]
    for face in mesh["faces"]:
        if face["group"]=="body": draw.polygon([(points[i].real,points[i].imag) for i,_ in face["corners"]],fill=1)
    image.save(out/"oracle_mask.png")
    buf=BytesIO();image.save(buf,format="PNG")
    fit=fit_body(body,SimpleNamespace(png=buf.getvalue()),alignment)
    assert fit.fitted_iou>fit.bootstrap_iou, (fit.bootstrap_iou,fit.fitted_iou)
    vertices=np.asarray(deform_vertices(body,fit.controls))
    posed_alignment=Alignment(camera,0,{"lowerarm01.L":.15})
    transforms=pose_transforms(rig,validate_rebind(body,vertices),posed_alignment)
    posed=np.asarray(skin_vertices(vertices,rig["skin"],transforms))
    validate_pose(body,vertices,posed)
    assert np.isfinite(posed).all() and np.max(np.abs(posed-vertices))>0
    texture=Image.new("RGB",(128,128))
    d=ImageDraw.Draw(texture)
    for y in range(0,128,16):
        for x in range(0,128,16): d.rectangle((x,y,x+15,y+15),fill=(150,170,190) if (x+y)//16%2 else (80,100,120))
    # Lab-only aliases: native morph_controls strips the last stem segment.
    from dataclasses import replace
    manifest=json.loads((Path(__file__).resolve().parents[2]/"lab/manifests/makehuman-anatomical-torso.json").read_text())
    extra={Path(i["path"]).name:i["sha256"] for i in manifest["files"]}
    targets=_morph_targets({n:read(n,h) for n,h in extra.items()},len(rest))
    body["morph_targets"].update({n.rsplit("-",1)[0]+"-lab-"+n.rsplit("-",1)[1]:v for n,v in targets.items()})
    checks={}
    controls={}
    for name in ("torso-scale-depth","torso-scale-horiz","torso-vshape"):
        for value in (-.25,.25):
            v=np.asarray(deform_vertices(body,{name:value}))
            assert np.isfinite(v).all() and np.array_equal(v,np.asarray(deform_vertices(body,{name:value})))
            delta=float(np.max(np.abs(v-rest)))
            assert delta>0
            checks[name+str(value)]=delta
        controls[name]=.25
    fit_expanded=replace(fit,controls=fit.controls|controls)
    expanded=np.asarray(deform_vertices(body,fit_expanded.controls))
    t=pose_transforms(rig,validate_rebind(body,expanded),posed_alignment)
    ep=np.asarray(skin_vertices(expanded,rig["skin"],t))
    validate_pose(body,expanded,ep)
    assert np.isfinite(ep).all() and np.max(np.abs(ep-expanded))>0
    export_body(out/"human.usdz",body,fit_expanded,posed_alignment,texture=texture,ground=True)
    metrics={"scope":"known geometry oracle silhouette; calibrated camera; native fit and export","bootstrap_iou":fit.bootstrap_iou,"fitted_iou":fit.fitted_iou,"controls":fit.controls,"vertices":len(vertices),"bones":len(rig["bones"]),"morph_max_delta":float(np.max(np.abs(truth-rest))),"pose_max_delta":float(np.max(np.abs(posed-vertices))),"asset_hashes":ASSETS|MORPH_ASSETS|extra,"expanded_morph_deltas":checks,"expanded_controls":controls,"expanded_pose_delta":float(np.max(np.abs(ep-expanded)))}
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2))
    print("NATIVE_CONTROL="+json.dumps(metrics))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();main(a.runtime,a.output)
