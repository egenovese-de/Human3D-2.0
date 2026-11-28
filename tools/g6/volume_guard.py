"""Construct a single inspectable spline field and screen its sampled determinant."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.sparse import eye
from scipy.sparse.linalg import factorized

from deformation import ffd
from human3d.frozen_body import load_project_body
from human3d.native_rig import validate_rebind
from human3d.session import Session


def main(args):
    for file in sorted(args.study.glob('*/accepted.npz')):
        began=perf_counter()
        case=file.parent.name
        with np.load(file) as d:
            anchor,target,ref,rf,faces=[d[k] for k in ('D0','R2_fine','reference','reference_faces','faces')]
        dim=(5,8,5)
        b,l=ffd(anchor,dim)
        x=factorized((b.T@b+.003*(l.T@l)+.0001*eye(b.shape[1])).tocsc())(b.T@(target-anchor))
        u=np.linspace(.025,.975,15)
        xyz=np.stack(np.meshgrid(u,u,u,indexing='ij'),-1).reshape(-1,3)
        probes=anchor.min(0)+xyz*np.ptp(anchor,axis=0)
        delta=[]
        for axis in np.eye(3):
            plus=ffd(np.r_[anchor,probes+axis*.005],dim)[0][-len(probes):]@x
            minus=ffd(np.r_[anchor,probes-axis*.005],dim)[0][-len(probes):]@x
            delta.append((plus-minus)/.01)
        j=np.stack(delta,axis=2)
        movement=b@x
        raw_min=float(np.linalg.det(np.eye(3)+j).min())
        body=load_project_body(Session(args.baseline/case/'calibrated'/'project').store)
        for alpha in (1.,.85,.7,.55,.4,.25,.125,0.):
            det=np.linalg.det(np.eye(3)+alpha*j)
            if det.min()<=.1:
                continue
            candidate=anchor+alpha*movement
            try:
                validate_rebind(body,candidate/10)
                break
            except ValueError:
                continue
        dest=args.output/case
        dest.mkdir(parents=True,exist_ok=True)
        key='R2_volume_checked'
        np.savez_compressed(dest/'proposals.npz',D0=anchor,reference=ref,reference_faces=rf,faces=faces,**{key:candidate})
        metadata={'sampled_determinants':len(det),'proposal_full_min_det':raw_min,
                  'pre_bvh_min_det':float(det.min()),'pre_bvh_accepted_fraction':alpha,
                  'seconds':perf_counter()-began,
                  'rms_embedding_error_mm':float(np.sqrt(np.mean(np.sum((target-anchor-movement)**2,axis=1)))*10)}
        # Record the same global scaling sequence the independent surface check can apply.
        metadata['combined_determinant_min_by_surface_fraction']={str(x):float(np.linalg.det(
            np.eye(3)+alpha*x*j).min()) for x in (1.,.75,.5,.25,.125,.0625,0.)}
        (dest/'fit.json').write_text(json.dumps({'study':{key:metadata}},indent=2))
        print(case,metadata['pre_bvh_min_det'],alpha,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('study','baseline','output'):
        p.add_argument(k,type=Path)
    main(p.parse_args())
