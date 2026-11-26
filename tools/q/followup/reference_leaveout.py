"""Withhold the same labeled profile from each four-view fit, then score it."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask
from human3d.alignment import initialize_alignment
from human3d.fitting import _optimize, _scorer
from human3d.frozen_body import deform_vertices, load_project_body, morph_controls
from human3d.proportions import length_controls
from human3d.regional_morphs import regional_controls
from human3d.session import Session


def run(previous, output):
    results = []
    for folder in sorted((previous/"holdout").glob("*_bend0")):
        metadata=json.loads((folder/"manifest.json").read_text())
        train=json.loads((folder/"native-4.json").read_text())["images"]
        angles={entry["sha256"]:entry["yaw"] for entry in train}
        session=Session(previous/"holdout-native"/(folder.name+"-4")/"project")
        body=load_project_body(session.store)
        base=np.asarray(deform_vertices(body,{}))
        faces=[tuple(i for i,_ in face["corners"]) for face in body["mesh"]["faces"] if face["group"]=="body"]
        elevations=base[np.unique(np.concatenate(faces)),1]
        height=np.ptp(np.asarray(json.loads((folder/"mesh.json").read_text())["vertices"])[:,2])
        available={angles[view.ref.photo_digest]:view for view in session.shared_evidence().views if view.mask}
        held=90
        if held not in available or len(available)<3:
            results.append(dict(identity=metadata["identity"],error="insufficient_profile_leaveout_masks"))
            continue
        selected={k:v for k,v in available.items() if k!=held}
        buffers={k:v.mask for k,v in selected.items()}
        cameras={k:initialize_alignment(body,v.detection,v.candidate,refine=True) for k,v in selected.items()}
        start=perf_counter()
        score=_scorer(body,buffers,cameras,base)
        names=(*morph_controls(body),*length_controls(body),*regional_controls(body))
        controls,_=_optimize(body,score,{},names,(.25,.125))
        points=deform_vertices(body,controls)
        withheld=available[held]
        proxy=_scorer(body,{held:withheld.mask},{held:initialize_alignment(body,withheld.detection,withheld.candidate,refine=True)},base)

        def truth_scores(values):
            vertices=np.asarray(values).copy()
            vertices[:,1]-=elevations.min()
            vertices*=10*height/np.ptp(elevations)
            scores={}
            for image in metadata["images"]:
                if image["held_out"]:
                    mask=load_mask(folder/image["file"])
                    scores[image["yaw"]]=compare(mask,silhouette(vertices,faces,camera_for(image["yaw"],height),mask.size))["iou"]
            return scores

        results.append(dict(identity=metadata["identity"],omitted_yaw=held,fit_yaws=list(selected),controls=controls,
            withheld_view_proxy_iou_change=proxy(points)[held]-proxy(base)[held],elapsed_seconds=perf_counter()-start,
            bootstrap_held_out_iou=truth_scores(base),fit_held_out_iou=truth_scores(points)))
        output.write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("previous",type=Path)
    parser.add_argument("output",type=Path)
    run(**vars(parser.parse_args()))
