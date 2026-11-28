"""Sample interpolated volume Jacobians and retained held-out silhouette agreement."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.sparse import eye
from scipy.sparse.linalg import factorized

from deformation import ffd
from photo import iou
from projection import Raster


def main(root,raster_path):
    raster=Raster(raster_path)
    data={'lattice_jacobian':{},'heldout_iou':{}}
    for file in sorted((root/'study').glob('*/accepted.npz')):
        with np.load(file) as d:
            base=d['R0_long']
            outcome=d['R2_fine']
            dims=(5,8,5)
            b,l=ffd(base,dims)
            solve=factorized((b.T@b+.001*(l.T@l)+.0001*eye(b.shape[1])).tocsc())
            offsets=solve(b.T@(outcome-base))
            u=np.linspace(.04,.96,13)
            grid=np.stack(np.meshgrid(u,u,u,indexing='ij'),-1).reshape(-1,3)
            probes=base.min(0)+grid*np.ptp(base,axis=0)
            step=.005
            deriv=[]
            for axis in np.eye(3):
                fp=ffd(np.vstack([base,probes+step*axis]),dims)[0][-len(probes):] @ offsets
                fm=ffd(np.vstack([base,probes-step*axis]),dims)[0][-len(probes):] @ offsets
                deriv.append(axis+(fp-fm)/(2*step))
            det=np.linalg.det(np.stack(deriv,axis=-1))
            mismatch=np.linalg.norm(b@offsets-(outcome-base),axis=1)*10
            data['lattice_jacobian'][file.parent.name]={'samples':len(det),'min':float(det.min()),
                'p01':float(np.percentile(det,1)),'p99':float(np.percentile(det,99)),
                'nonpositive':int((det<=0).sum()),'reembedded_field_vertex_mean_error_mm':float(mismatch.mean())}
    for group in ('photo','oracle'):
        for file in sorted((root/group).glob('*/accepted.npz')):
            with np.load(file) as d:
                data['heldout_iou'][group+'/'+file.parent.name]={
                 k:iou(raster,d[k],d['faces'],d['reference'],d['reference_faces']) for k in d.files
                 if k not in ('reference','reference_faces','faces')}
    (root/'diagnostics.json').write_text(json.dumps(data,indent=2,allow_nan=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    parser.add_argument('raster',type=Path)
    args=parser.parse_args()
    main(args.root,args.raster)
