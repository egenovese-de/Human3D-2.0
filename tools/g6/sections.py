"""Fixed-plane anatomical section loops and approximate local morphology."""
import argparse
import json
from pathlib import Path

import numpy as np

from section_loops import directed, geometry, torso_loop
from human3d.frozen_body import load_project_body
from human3d.native_rig import rebind_joints
from human3d.session import Session


def conditioned_loop(points, faces, origin, normal):
    n=normal/np.linalg.norm(normal)
    right=np.cross(n,[0,0,1.])
    if np.linalg.norm(right)<.12:
        right=np.cross(n,[1,0,0.])
    right/=np.linalg.norm(right)
    anterior=np.cross(right,n)
    centered=(points-origin) @ np.stack([right,n,anterior]).T
    return torso_loop(centered,faces,0)


def main(args):
    measurements={}
    draft={}
    for folder in sorted(args.study.iterdir()):
        if not (folder/'accepted.npz').exists():
            continue
        case=folder.name
        with np.load(folder/'accepted.npz') as item:
            ref,rf,faces=(item[k] for k in ('reference','reference_faces','faces'))
            lo,hi=ref[np.unique(rf),1].min(),ref[np.unique(rf),1].max()
            planes={label:(np.array([0,lo+t*(hi-lo),0]),np.array([0,1,0]))
                    for label,t in [('chest_diagnostic',.75),('abdomen',.675),('waist',.62),('hip',.535)]}
            if case.startswith('A_'):
                body=load_project_body(Session(args.baseline/case/'calibrated'/'project').store)
                rig=body['rig']
                joints=rebind_joints(rig,ref/10)
                for label,name in [('upper_arm_L','upperarm01.L'),('thigh_L','upperleg01.L'),
                                   ('calf_L','lowerleg01.L')]:
                    b=rig['bones'][name]
                    a,z=joints[b['head']]*10,joints[b['tail']]*10
                    # In the oblique frame, connected torso loops can still
                    # intersect the plane. Select using the isolated bone-side area.
                    planes[label]=(a*.5+z*.5,z-a)
            rows=measurements[case]={}
            for label,(origin,normal) in planes.items():
                def get(points, triangles):
                    if label.endswith('_L'):
                        # Clip away torso and contralateral connected loops.
                        # A clipped or open section is explicitly unavailable.
                        below=(points[triangles,0] < (origin[0]-.25*abs(origin[0]))).any(1)
                        triangles=triangles[~below]
                    return conditioned_loop(points,triangles,origin,normal)
                try:
                    area,ring=get(ref,rf)
                    circum=geometry(ring)[2].sum()
                except ValueError as e:
                    rows[label]={'reference_unavailable':str(e)}
                    continue
                row=rows[label]={'reference_area_cm2':area,'circumference_cm':float(circum),
                                 'axis_cm':origin.tolist(),'normal':(normal/np.linalg.norm(normal)).tolist(),'fits':{}}
                if case=='A_slim':
                    draft[label]={'reference':ring.tolist()}
                for k in ('D0','R1_extended','R2_fine','R3_cage','R4_graph120','R5_symmetric','R6_graph'):
                    try:
                        a,r=get(item[k],faces)
                        dist=np.r_[directed(r,ring),directed(ring,r)]*10
                    except ValueError as e:
                        row['fits'][k]={'unavailable':str(e)}
                        continue
                    row['fits'][k]={'area_error_cm2':float(a-area),
                                    'circumference_signed_mm':float((geometry(r)[2].sum()-circum)*10),
                                    'shape_mean_mm':float(dist.mean()),'shape_p95_mm':float(np.percentile(dist,95)),
                                    'width_error_mm':float((np.ptp(r[:,0])-np.ptp(ring[:,0]))*10),
                                    'depth_error_mm':float((np.ptp(r[:,1])-np.ptp(ring[:,1]))*10)}
                    if case=='A_slim':
                        draft[label][k]=r.tolist()
    args.output.write_text(json.dumps(measurements,indent=2,allow_nan=False))
    args.output.with_name('section_plot_data.json').write_text(json.dumps(draft))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('study','baseline','output'):
        p.add_argument(name,type=Path)
    main(p.parse_args())
