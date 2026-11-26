"""Test upstream adult MakeHuman targets as alternate Lab-only canonical bases."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from evaluate import sample_surface
from human3d.bootstrap import _morph_targets
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import validate_rebind
from human3d.session import Session


def run(previous, output):
    rows = []
    for folder in sorted((previous/"holdout").glob("*_bend0")):
        meta = json.loads((folder/"manifest.json").read_text())
        truth = json.loads((folder/"mesh.json").read_text())
        xyz = np.asarray(truth["vertices"])
        height = np.ptp(xyz[:,2])
        truth_samples = sample_surface(xyz,truth["faces"],12000,2474)
        tree = cKDTree(truth_samples)
        body = load_project_body(Session(previous/"holdout-native"/(folder.name+"-1")/"project").store)
        base = np.asarray(deform_vertices(body, {}))
        faces = [tuple(i for i,_ in face["corners"]) for face in body["mesh"]["faces"] if face["group"]=="body"]
        body_vertices=np.unique(np.concatenate(faces))
        alternatives = {"bootstrap":(base,None)}
        for name in ("caucasian-female-young.target","caucasian-male-young.target"):
            data = (previous/"assets"/name).read_bytes()
            offsets = np.asarray(_morph_targets({name:data},len(base))[name.removesuffix(".target")])
            neutral = base.copy()
            neutral[offsets[:,0].astype(int)] += offsets[:,1:]
            alternatives[name] = (neutral,sha256(data).hexdigest())
        records=[]
        for name,(neutral,digest) in alternatives.items():
            record={"condition":name,"asset_sha256":digest}
            try:
                validate_rebind(body,neutral)
            except ValueError as error:
                record.update(validation_error=str(error))
            else:
                x,y,z=neutral.T
                vertical=y[body_vertices]
                world=np.column_stack((x,-z,y-vertical.min()))*(height/np.ptp(vertical))
                sample=sample_surface(world,faces,12000,2474)
                record["symmetric_mean_mm"]=float(500*(tree.query(sample)[0].mean()+cKDTree(sample).query(truth_samples)[0].mean()))
            records.append(record)
        rows.append(dict(identity=meta["identity"],conditions=records))
    output.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("previous",type=Path)
    parser.add_argument("output",type=Path)
    run(**vars(parser.parse_args()))
