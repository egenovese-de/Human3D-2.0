"""Bounded Lab-only independent-to-native surface transfer and contract probes."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.spatial import cKDTree

from evaluate import metric_distance, sample_surface
from human3d.appearance import prepare_view
from human3d.originals import OriginalStore
from human3d.texture_bake import bake_atlas
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import measure_clearance, prototype
from human3d.native_rig import pose_transforms, skin_vertices, validate_pose, validate_rebind
from human3d.session import Session


BASIS = np.array(((1,0,0),(0,0,-1),(0,1,0)))


def skin(vertices, rig, alignment, joints):
    return skin_vertices(vertices, rig["skin"], pose_transforms(rig, joints, alignment))


def transfer(native, truth, faces, limit):
    valid = np.unique(np.concatenate(faces))
    tree = cKDTree(truth)
    _, nearest = tree.query(native[valid])
    displacement = np.zeros_like(native)
    delta = truth[nearest]-native[valid]
    displacement[valid] = delta * np.minimum(1,limit/np.maximum(np.linalg.norm(delta,axis=1),1e-8))[:,None]
    pairs = {(a,b) for face in faces for a,b in zip(face,face[1:]+face[:1])}
    pairs |= {(b,a) for a,b in pairs}
    first,last = np.array(sorted(pairs)).T
    weights = np.bincount(first,minlength=len(native))
    graph = coo_matrix((1/weights[first],(first,last)),shape=(len(native),len(native))).tocsr()
    for _ in range(6):
        displacement = .45*displacement+.55*(graph@displacement)
    return displacement


def main(previous, output):
    rows = []
    for folder in sorted((previous/"holdout").glob("*_bend0")):
        meta = json.loads((folder/"manifest.json").read_text())
        mesh = json.loads((folder/"mesh.json").read_text())
        truth = np.asarray(mesh["vertices"])
        height = np.ptp(truth[:,2])
        project = previous/"holdout-native"/(folder.name+"-1")/"project"
        session = Session(project)
        body = load_project_body(session.store)
        rig = body["rig"]
        base = np.asarray(deform_vertices(body,{}))
        faces = [tuple(i for i,_ in f["corners"]) for f in body["mesh"]["faces"] if f["group"]=="body"]
        y=base[np.unique(np.concatenate(faces)),1]
        factor=height/np.ptp(y)
        world=lambda v:(np.asarray(v)@BASIS.T-(0,0,y.min()))*factor
        actual = sample_surface(truth,mesh["faces"],12000,2473)
        tree = cKDTree(actual)
        regions={"head":(.86*height,height+1e-8),"torso_and_arms":(.54*height,.86*height),"lower_body":(-1e-8,.54*height)}
        fit=session.current_shared_fit()
        view=session.shared_evidence().views[0]
        alignment=fit.alignments[view.ref.photo_id]
        record={"identity":meta["identity"],"source_mesh_sha256":meta["mesh_sha256"],"conditions":[]}
        appearance = prepare_view(OriginalStore(project),view,alignment)
        for name, change in (
            ("exact_contract_control",np.zeros_like(base)),
            ("registered_bounded_12mm",transfer(world(base),actual,faces,.012)@BASIS/factor),
            ("registered_bounded_24mm",transfer(world(base),actual,faces,.024)@BASIS/factor),
            ("registered_damped_03mm",transfer(world(base),actual,faces,.012)@BASIS/factor*.25),
            ("registered_damped_0p6mm",transfer(world(base),actual,faces,.012)@BASIS/factor*.05),
        ):
            neutral=base+change
            entry=dict(condition=name,maximum_transfer_mm=float(np.linalg.norm(change,axis=1).max()*factor*1000),
                       distance_before_pose=metric_distance(actual,tree,sample_surface(world(neutral),faces,12000,2474),regions))
            record["conditions"].append(entry)
            try:
                joints=validate_rebind(body,neutral)
                posed=skin(neutral,rig,alignment,joints)
                validate_pose(body,neutral,posed)
                garment=prototype(body,neutral,"top")
                shell=skin_vertices(garment.points,garment.skin,pose_transforms(rig,joints,alignment))
                clearance=measure_clearance(garment,body,posed,shell)
                entry.update(native_rebind_passed=True,native_pose_passed=True,
                             native_top_clearance_mm=clearance.minimum*100,native_top_violations=clearance.violations,
                             topology_uv_skin_preserved=True)
                adapted = body | {"mesh":body["mesh"] | {"vertices":neutral.tolist()}}
                try:
                    atlas = bake_atlas(adapted,{},{"front":(appearance,view.detection.image_size)},"front",size=128)
                except ValueError as error:
                    entry["texture_validation_error"] = str(error)
                else:
                    entry["texture_uv_coverage"] = atlas.observed_fraction
            except ValueError as error:
                entry["validation_error"]=str(error)
        rows.append(record)
        output.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("previous",type=Path)
    parser.add_argument("output",type=Path)
    main(**vars(parser.parse_args()))
