"""Register independent ring garments into the native USD skin contract."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import (Garment, GarmentAsset, _normals, _body_faces,
    correct_clearance, measure_clearance, posed_garment, verify_layers, repair_garment_contacts, _triangulate)
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.usd_export import export_body
from human3d.triangle_collision import triangle_contact_pairs


def layer_locations(inner, outer, transforms):
    a, b = _triangulate(inner.faces), _triangulate(outer.faces)
    states = {"neutral": (inner.points, outer.points),
              "posed": (posed_garment(inner, transforms), posed_garment(outer, transforms))}
    return {state: [{"inner": i, "outer": j, "kind": kind,
                     "outer_center_dm": other[b[j]].mean(0).tolist(),
                     "outer_dominant_bones": sorted({max(outer.skin[k], key=outer.skin[k].get) for k in b[j]})}
                    for i, j, kind in triangle_contact_pairs(first[a], other[b]) if kind != "touching"]
            for state, (first, other) in states.items()}


def run(previous, clothing, output, report, *, exact_repair=False):
    result=[]
    for identity in ("f_af01","m_la01"):
        project=next((previous/"holdout-native").glob(f"*_{identity}_bend32-1"))/"project"
        session=Session(project)
        body=load_project_body(session.store)
        fit=session.current_shared_fit()
        view=session.shared_evidence().views[0]
        alignment=fit.alignments[view.ref.photo_id]
        vertex=np.asarray(deform_vertices(body,fit.fit.controls))
        rig=body["rig"]
        native_indices=np.unique([i for f in body["mesh"]["faces"] if f["group"]=="body" for i,_ in f["corners"]])
        floor=vertex[native_indices,1].min()
        true=np.asarray(json.loads((next((previous/"holdout").glob(f"*_{identity}_bend0"))/"mesh.json").read_text())["vertices"])
        scale=np.ptp(vertex[native_indices,1])/np.ptp(true[:,2])
        transforms=pose_transforms(rig,rebind_joints(rig,vertex),alignment)
        posed=skin_vertices(vertex,rig["skin"],transforms)
        layers=[]
        metadata={"identity":identity,"attempts":[]}
        for layer in (0,1):
            path=clothing/identity/"layered"/f"layer_{layer}.json"
            data=json.loads(path.read_text())
            x,y,z=np.asarray(data["vertices"]).T
            layer_id=(np.arange(len(z))%48)/48
            layer_height=(z-z.min())/np.ptp(z)
            uv=tuple(zip(layer_id.tolist(),layer_height.tolist()))
            layer_faces=tuple(tuple((i,i) for i in face) for face in data["faces"])
            geometry=np.column_stack((x*scale,z*scale+floor,-y*scale))
            layers.append((geometry,uv,layer_faces))
        raw=layers[0][0]
        available=native_indices[(vertex[native_indices,1]>raw[:,1].min()-.3)&
                                 (vertex[native_indices,1]<raw[:,1].max()+.3)&
                                 (np.abs(vertex[native_indices,0])<np.abs(raw[:,0]).max()+.35)]
        distances=cdist(raw,vertex[available])
        row_id,col_id=linear_sum_assignment(distances)
        if len(row_id)!=len(raw) or not np.array_equal(row_id,np.arange(len(raw))):
            raise ValueError("canonical correspondence assignment underspecified")
        matched=available[col_id]
        normals=_normals(posed,_body_faces(body))[matched]
        blends=np.asarray([sum((w*transforms[n][0] for n,w in rig["skin"][i].items()),
                               np.zeros((3,3))) for i in matched])
        inverse=np.linalg.pinv(blends,rcond=.06)
        metadata["transfer_distance_mean_m"]=float(distances[row_id,col_id].mean()/scale)
        metadata["transfer_distance_p95_m"]=float(np.quantile(distances[row_id,col_id],.95)/scale)
        for attempt_scale,repair in ((1,False),(1.12,False),(1.24,False),(1.08,True),(1.25,True)):
            attempt={"radial_expansion":attempt_scale,"layer_projection_repair":repair,"layers":[]}
            metadata["attempts"].append(attempt)
            assets=[]
            for layer,(geometry,uv,mesh) in enumerate(layers):
                points=geometry.copy()
                for axis in (0,2):
                    points[:,axis]*=attempt_scale
                suffix=("base","outer")[layer]
                cloth=Garment("independent_"+suffix,"top",layer,points,mesh,uv,
                              tuple(rig["skin"][i] for i in matched),tuple(int(i) for i in matched),0)
                cloth,clearance=correct_clearance(cloth,body,posed,transforms)
                attempt["layers"].append({"violations":clearance.violations,"clearance_mm":100*clearance.minimum})
                assets.append(GarmentAsset(cloth,Image.new("RGB",(128,128),((43,85,168),(163,75,41))[layer]),0))
            folder=output/identity
            folder.mkdir(parents=True,exist_ok=True)
            try:
                layer=verify_layers([a.garment for a in assets],body,posed,transforms)
                if layer:
                    attempt["layer_clearance_mm"]=100*layer.minimum
                if repair:
                    inner,outer=(asset.garment for asset in assets)
                    original=outer.points.copy()
                    for _ in range(4):
                        a,b=(posed_garment(g,transforms) for g in (inner,outer))
                        gaps=np.einsum("ij,ij->i",b-a,normals)
                        move=np.clip(.07-gaps,0,.45)[:,None]*normals
                        rest_move=np.einsum("ijk,ik->ij",inverse,move)
                        outer=replace(outer,points=outer.points+rest_move)
                        outer,_=correct_clearance(outer,body,posed,transforms)
                    assets[1]=replace(assets[1],garment=outer)
                    attempt["repair_peak_rest_delta_mm"]=float(100*np.linalg.norm(outer.points-original,axis=1).max())
                    attempt["post_repair_layer_min_mm"]=100*verify_layers([inner,outer],body,posed,transforms).minimum
                    attempt["post_repair_body_min_mm"]=100*measure_clearance(outer,body,posed,posed_garment(outer,transforms)).minimum
                if exact_repair:
                    inner,outer=(asset.garment for asset in assets)
                    before = layer_locations(inner, outer, transforms)
                    repaired_inner = repair_garment_contacts(inner, body, vertex, posed, transforms)
                    repaired_outer = repair_garment_contacts(outer, body, vertex, posed, transforms, inner=repaired_inner)
                    attempt["exact_repair"] = {
                        "before": before, "after": layer_locations(repaired_inner, repaired_outer, transforms),
                        "peak_outer_displacement_mm": float(np.linalg.norm(repaired_outer.points - outer.points, axis=1).max() * 100),
                    }
                    assets[0] = replace(assets[0], garment=repaired_inner)
                    assets[1] = replace(assets[1], garment=repaired_outer)
                export_body(folder/"independent.usdz",body,fit.fit,alignment,texture=Image.new("RGB",(128,128),(164,111,81)),garments=assets)
            except ValueError as error:
                attempt["error"]=str(error)
                continue
            attempt["exported"]=True
            break
        result.append(metadata)
        report.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("previous","clothing","output","report"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--exact-repair", action="store_true")
    run(**vars(parser.parse_args()))
