"""Replay the saved native-pose factorial cell with a second camera/shape pass."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.spatial import cKDTree

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from human3d.fitting import _optimize, _refine_silhouette_cameras, _scorer
from human3d.frozen_body import deform_vertices, load_project_body, morph_controls
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.proportions import length_controls
from human3d.regional_morphs import regional_controls
from human3d.session import Session


def run(previous, factorial, output):
    results = []
    for record in json.loads(factorial.read_text()):
        identity = record["identity"]
        folder=next((previous/"holdout").glob(f"*_{identity}_bend32"))
        meta=json.loads((folder/"manifest.json").read_text())
        truth=json.loads((folder/"mesh.json").read_text())
        reference=np.asarray(truth["vertices"])
        height=np.ptp(reference[:,2])
        session=Session(previous/"holdout-native"/(folder.name+"-1")/"project")
        view=session.shared_evidence().views[0]
        native=session.current_shared_fit().alignments[view.ref.photo_id]
        body=load_project_body(session.store)
        rig=body["rig"]
        faces=[tuple(i for i,_ in f["corners"]) for f in body["mesh"]["faces"] if f["group"]=="body"]
        base=np.asarray(deform_vertices(body,{}))
        rest_y=base[np.unique(np.concatenate(faces)),1]
        factor=height/np.ptp(rest_y)
        samples=sample_surface(reference,truth["faces"],12000,2473)
        tree=cKDTree(samples)
        bands={"head":(.86*height,height+1e-8),"torso_and_arms":(.54*height,.86*height),"lower_body":(-1e-8,.54*height)}
        original=next(c for c in record["cells"] if (c["camera"],c["pose"],c["shape"])==("native","native","fitted"))
        controls=original["controls"]
        start=perf_counter()
        verts=deform_vertices(body,controls)
        adjusted=_refine_silhouette_cameras(body,verts,{0:view.mask},{0:native})
        score=_scorer(body,{0:view.mask},adjusted,verts)
        names=(*morph_controls(body),*length_controls(body),*regional_controls(body))
        values,scores=_optimize(body,score,controls,names,(.125,))
        neutral=deform_vertices(body,values)
        pose=pose_transforms(rig,rebind_joints(rig,neutral),adjusted[0])
        x,y,z=skin_vertices(neutral,rig["skin"],pose).T
        world=np.column_stack((x,-z,y-rest_y.min()))*factor
        projected=10*np.column_stack((world[:,0],world[:,2],-world[:,1]))
        evaluation={}
        for row in meta["images"]:
            if row["held_out"]:
                mask=load_mask(folder/row["file"])
                evaluation[row["yaw"]]=compare(mask,silhouette(projected,faces,camera_for(row["yaw"],height),mask.size))["iou"]
        results.append(dict(identity=identity,source_mesh_sha256=meta["mesh_sha256"],controls=values,
         new_train_iou=scores[0],old_train_iou=original["training_mask_iou"],
         additional_seconds=perf_counter()-start,held_out_iou=evaluation,
         original_held_out_iou={k:v for k,v in original["fixed_camera_iou"].items() if k!="0"},
         baseline_surface_mm=original["symmetric_mean_mm"],
         **metric_distance(samples,tree,sample_surface(world,faces,12000,2473),bands)))
        output.write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("previous","factorial","output"):
        parser.add_argument(name,type=Path)
    run(**vars(parser.parse_args()))
