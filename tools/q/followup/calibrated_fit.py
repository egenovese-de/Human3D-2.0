"""Fit calibrated four-view silhouettes and evaluate against identical held-out views."""
import argparse
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.spatial import cKDTree

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from human3d.alignment import Alignment
from human3d.fitting import _optimize, _scorer
from human3d.frozen_body import deform_vertices, load_project_body, morph_controls
from human3d.mask_review import SubjectMask
from human3d.proportions import length_controls
from human3d.regional_morphs import regional_controls
from human3d.session import Session


def run(previous, output):
    rows = json.loads(output.read_text()) if output.exists() else []
    completed = {row["identity"] for row in rows}
    for folder in sorted((previous/"holdout").glob("*_bend0")):
        meta = json.loads((folder/"manifest.json").read_text())
        identity = meta["identity"]
        if identity in completed:
            continue
        body = load_project_body(Session(previous/"holdout-native"/(folder.name+"-4")/"project").store)
        mesh = json.loads((folder/"mesh.json").read_text())
        target = np.asarray(mesh["vertices"])
        height = np.ptp(target[:,2])
        base = np.asarray(deform_vertices(body,{}))
        faces = [tuple(i for i,_ in f["corners"]) for f in body["mesh"]["faces"] if f["group"]=="body"]
        elevations = base[np.unique(np.concatenate(faces)),1]
        factor = height / np.ptp(elevations)
        floor = elevations.min()
        masks, alignments, evaluation = {}, {}, {}
        for view in meta["images"]:
            yaw = view["yaw"]
            if view["held_out"]:
                evaluation[yaw] = load_mask(folder/view["file"])
            elif yaw in (0,90,180,270):
                binary = BytesIO()
                load_mask(folder/view["file"]).save(binary,format="PNG")
                masks[yaw] = SubjectMask(view["sha256"],0,binary.getvalue())
                c = camera_for(yaw,height)
                alignments[yaw] = Alignment(replace(c,similarity=c.similarity*10*factor,
                    origin=c.origin+c.similarity*complex(0,floor*factor*10)),0,{})
        start = perf_counter()
        score = _scorer(body,masks,alignments,base)
        supported = (*morph_controls(body),*length_controls(body),*regional_controls(body))
        values, training = _optimize(body,score,{},supported,(.25,.125))
        duration = perf_counter()-start
        x,y,z = np.asarray(deform_vertices(body,values)).T
        world = np.column_stack((x,-z,y-floor))*factor
        model = np.column_stack((world[:,0],world[:,2],-world[:,1]))*10
        truth = sample_surface(target,mesh["faces"],12000,2474)
        bands = {"head": (.86*height,height+1e-8),"torso_and_arms": (.54*height,.86*height),"lower_body": (-1e-8,.54*height)}
        rows.append(dict(identity=identity,fixture_sha256=meta["mesh_sha256"],training_iou=training,controls=values,
            held_out_iou={yaw:compare(mask,silhouette(model,faces,camera_for(yaw,height),mask.size))["iou"]
                          for yaw,mask in evaluation.items()},
            fit_seconds=duration,
            **metric_distance(truth,cKDTree(truth),sample_surface(world,faces,12000,2474),bands)))
        output.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("previous",type=Path)
    parser.add_argument("output",type=Path)
    run(**vars(parser.parse_args()))
