"""Test cranial/profile targets and independent MB-Lab expressions."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from evaluate import sample_surface
from face_capacity import descriptive, skull
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.session import Session


def run(dataset, previous, output):
    rows=[]
    for identity in ("f_af01","m_la01"):
        root=dataset/f"{identity}_neutral"
        meta=json.loads((root/"manifest.json").read_text())
        mesh=json.loads((root/"mesh.json").read_text())
        truth=np.asarray(mesh["vertices"])
        top=truth[:,2].max()
        expression=previous/"mblab/data/expressions_morphs"/f"{identity}_exprs.json"
        morphs=json.loads(expression.read_text())
        candidates={"neutral":truth}
        for label,name in (("open_jaw","mouthOpenLarge"),("smile","mouthSmile"),("left_cheek","cheekSneerL")):
            delta=np.asarray(morphs[f"Expressions_{name}_max"])
            changed=truth.copy()
            changed[delta[:,0].astype(int)] += delta[:,1:]
            candidates[label]=changed
        y_scale=np.exp(-((top-truth[:,2]-.06)/.055)**2)
        for width,depth in ((1.08,1.10),(.94,.91)):
            changed=truth.copy()
            changed[:,0]*=1+(width-1)*y_scale
            changed[:,1]*=1+(depth-1)*y_scale
            candidates[f"cranial_width{width}_depth{depth}"]=changed
        active=np.asarray(morphs["Expressions_nostrilsExpansion_max"])
        weight=np.linalg.norm(active[:,1:],axis=1)
        anchor=np.average(truth[active[:,0].astype(int)],axis=0,weights=weight)
        changes=truth.copy()
        normalized=(truth-anchor)/np.array((.033,.028,.028))
        changes[:,1]-=.018*np.exp(-np.square(normalized).sum(axis=1))
        candidates["nose_projection"]=changes

        project=next((previous/"holdout-native").glob(f"*_{identity}_bend0-1"))/"project"
        body=load_project_body(Session(project).store)
        faces=[tuple(i for i,_ in f["corners"]) for f in body["mesh"]["faces"] if f["group"]=="body"]
        base=np.asarray(deform_vertices(body,{}))
        elevation=base[np.unique(np.concatenate(faces)),1]
        factor=meta["height_m"]/np.ptp(elevation)
        release=[]
        for width in (-.5,-.25,0,.25,.5):
            for jaw in (-.5,-.25,0,.25,.5):
                x,y,z=np.asarray(deform_vertices(body,{"head_width":width,"jaw_width":jaw})).T
                world=np.column_stack((x,-z,y-elevation.min()))*factor
                sample=skull(sample_surface(world,faces,45000,2473),top)
                release.append((width,jaw,sample,cKDTree(sample)))
        for label,changed in candidates.items():
            target=skull(sample_surface(changed,mesh["faces"],45000,2473),top)
            tree=cKDTree(target)
            scores=[(float(500*(tree.query(sample)[0].mean()+sample_tree.query(target)[0].mean())),w,j)
                    for w,j,sample,sample_tree in release]
            initial=next(score for score,w,j in scores if w==j==0)
            optimum=min(scores)
            rows.append(dict(identity=identity,treatment=label,expression_source_sha256=sha256(expression.read_bytes()).hexdigest(),
                        max_controlled_vertex_change_mm=float(1000*np.linalg.norm(changed-truth,axis=1).max()),
                        baseline_symmetric_mm=initial,best_symmetric_mm=optimum[0],
                        best_head_width=optimum[1],best_jaw_width=optimum[2],
                        reference_profile=descriptive(target,top)))
    output.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("dataset","previous","output"):
        p.add_argument(name,type=Path)
    run(**vars(p.parse_args()))
