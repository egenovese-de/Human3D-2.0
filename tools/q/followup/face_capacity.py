"""Bound the release face controls against independent cranial profiles."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from evaluate import sample_surface
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.session import Session


def skull(samples, top):
    return samples[(samples[:, 2] > top-.235) & (np.abs(samples[:, 0]) < .16)]


def descriptive(samples, top):
    rows = {}
    for label, lo, hi in (("cranial", .01, .09), ("midface", .09, .155), ("jaw_band", .155, .205)):
        band = samples[(samples[:,2] > top-hi) & (samples[:,2] <= top-lo)]
        width, depth = np.diff(np.quantile(band[:, :2], [.025,.975], axis=0), axis=0)[0]*1000
        rows[label] = dict(width_mm=float(width), depth_mm=float(depth),
                           frontal_envelope_mm=float(-1000*np.quantile(band[:,1], .025)))
    return rows


def run(dataset, previous, output):
    path = next((previous / "holdout-native").glob("*_f_af01_bend0-1")) / "project"
    body = load_project_body(Session(path).store)
    faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
    base = np.asarray(deform_vertices(body, {}))
    elevations = base[np.unique(np.concatenate(faces)),1]
    controls = [(w, j, np.asarray(deform_vertices(body, {"head_width":w,"jaw_width":j})))
                for w in (-.5,-.25,0,.25,.5) for j in (-.5,-.25,0,.25,.5)]
    rows = []
    for folder in sorted(dataset.glob("*_neutral")):
        meta = json.loads((folder/"manifest.json").read_text())
        if not meta["source_family"].startswith("human") or meta["morphology_asymmetry"]:
            continue
        mesh = json.loads((folder/"mesh.json").read_text())
        xyz = np.asarray(mesh["vertices"])
        top = float(xyz[:,2].max())
        truth = skull(sample_surface(xyz,mesh["faces"],45000,2473),top)
        tree = cKDTree(truth)
        f = meta["height_m"]/np.ptp(elevations)
        metrics = []
        for width, jaw, coordinates in controls:
            x,y,z = coordinates.T
            converted = np.column_stack((x,-z,y-elevations.min()))*f
            p = skull(sample_surface(converted,faces,45000,2473),top)
            first, reverse = tree.query(p)[0], cKDTree(p).query(truth)[0]
            metrics.append(dict(head_width=width,jaw_width=jaw,symmetric_mean_mm=float(500*(first.mean()+reverse.mean())),
                                p95_mm=float(1000*np.quantile(np.r_[first,reverse],.95)), bands=descriptive(p,top)))
        rows.append(dict(identity=meta["identity"], source_family=meta["source_family"], mesh_sha256=meta["mesh_sha256"],
                         cranial_truth=descriptive(truth,top), candidates=metrics))
    output.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("dataset","previous","output"):
        parser.add_argument(name,type=Path)
    run(**vars(parser.parse_args()))
