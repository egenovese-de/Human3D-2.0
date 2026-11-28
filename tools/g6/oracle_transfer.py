"""Bounded volumetric fit with existing G5 exact-depth and normal agreement."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.sparse import csr_matrix, eye, kron, vstack
from scipy.sparse.linalg import lsqr

from deformation import ffd
from evidence import CONFIG,SIZE,visible_surface
from human3d.frozen_body import load_project_body
from human3d.native_rig import validate_rebind
from human3d.session import Session
from photo import iou
from projection import Camera,Raster


def solve(start, faces, ref, rf, raster, use_normals):
    b,l=ffd(start,(5,8,5))
    n=b.shape[1]
    reg=kron(l,eye(3),format='csr')
    penalty=eye(3*n,format='csr')
    cams=[Camera(y,**CONFIG['main_camera_cm']) for y in CONFIG['fit_yaw_deg'][:4]]
    captures=[visible_surface(raster,c,ref,rf,SIZE) for c in cams]
    current=start.copy()
    metric=[]
    for step in range(9):
        mats,replies=[],[]
        for c,truth in zip(cams,captures):
            draw=visible_surface(raster,c,current,faces,SIZE)
            valid=draw.valid&truth.valid
            y,x=np.nonzero(valid)
            idx=draw.triangle[y,x]
            if not len(idx):
                continue
            y,x,idx=y[::3],x[::3],idx[::3]
            triangles=faces[idx]
            rows=((b[triangles[:,0]]+b[triangles[:,1]]+b[triangles[:,2]])/3).tocoo()
            difference=truth.depth_cm[y,x]-draw.depth_cm[y,x]
            confidence=np.minimum(1.,3./np.maximum(np.abs(difference),1e-6))
            if use_normals:
                confidence*=np.clip(((draw.normals[y,x]*truth.normals[y,x]).sum(1)+.15)/1.15,.05,1.)
            conf=np.sqrt(confidence)
            direction=-c.axes()[2]
            design=csr_matrix((np.concatenate([rows.data*conf[rows.row]*direction[i] for i in range(3)]),
                   (np.tile(rows.row,3),np.concatenate([rows.col*3+i for i in range(3)]))),shape=(len(x),3*n))
            mats.append(design)
            replies.append(difference*conf)
        if not mats:
            break
        result=lsqr(vstack([*mats,4*reg,1.5*penalty]),np.r_[*replies,np.zeros(reg.shape[0]+penalty.shape[0])],iter_lim=100)
        shift=b@result[0].reshape(-1,3)
        delta=current-start+.65*shift
        current=start+delta*np.minimum(1,3.0/np.maximum(np.linalg.norm(delta,axis=1),1e-8))[:,None]
        metric.append({'step':step+1,'rows':sum(len(x) for x in replies),'LSQR':int(result[2]),'norm':float(result[3])})
    return current,metric


def main(a):
    with np.load(a.input/'accepted.npz') as r:
        source={k:r[k] for k in ('D0','faces','reference','reference_faces')}
    reference,rf,faces,start=[source[n] for n in ('reference','reference_faces','faces','D0')]
    raster=Raster(a.raster)
    folder=a.output/a.input.name
    folder.mkdir(parents=True,exist_ok=True)
    body=load_project_body(Session(a.baseline/a.input.name/'calibrated'/'project').store)
    rows={}
    for name,weight in [('P_oracle_depth',False),('P_oracle_depth_normals_weight',True)]:
        begin=perf_counter()
        proposed,curve=solve(start,faces,reference,rf,raster,weight)
        for alpha in (1.,.75,.5,.25,.125,0.):
            p=start+alpha*(proposed-start)
            try:
                validate_rebind(body,p/10)
                break
            except ValueError:
                continue
        source[name]=p
        rows[name]={'seconds':perf_counter()-begin,'initial_guard_fraction':alpha,'curve':curve,
                    'proposal_heldout_iou':iou(raster,p,faces,reference,rf)}
    (folder/'fit.json').write_text(json.dumps({'study':rows},indent=2,allow_nan=False))
    np.savez_compressed(folder/'proposals.npz',**source)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('input','baseline','raster','output'):
        p.add_argument(k,type=Path)
    main(p.parse_args())
