"""Fit bounded deformation from silhouette residuals with frozen view registration."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt
from scipy.sparse import csr_matrix, eye, kron, vstack
from scipy.sparse.linalg import lsqr

from deformation import adjacency, ffd, graph, unit_normals
from evidence import CONFIG, SIZE, resized, visible_surface
from human3d.experimental import NativeBasis
from human3d.frozen_body import load_project_body
from human3d.native_rig import validate_rebind
from human3d.session import Session
from observations import admit, observation_vertices
from projection import Camera, Raster
from refinement import refine
from observations import make_maps


def warp(anchor, faces, body, raster, observations, basis, smooth, *, steps=8):
    p = anchor.copy()
    notes = []
    dim = basis.shape[1]
    reg = kron(smooth, eye(3), format='csr')
    prior = eye(dim * 3, format='csr')
    for _ in range(steps):
        jac, targets = [], []
        for view, camera, mask in observations:
            posed = p if view is None else observation_vertices(body, p/10, view)*10
            drawn = visible_surface(raster,camera,posed,faces,SIZE)
            edge = drawn.mask & ~binary_erosion(drawn.mask)
            other = mask & ~binary_erosion(mask)
            if not edge.any() or not other.any():
                continue
            index = np.argwhere(edge)
            _, ni = distance_transform_edt(~other, return_indices=True)
            y,x = index.T
            nearest = ni[:,y,x].T
            _, reverse = distance_transform_edt(~edge,return_indices=True)
            by,bx=np.nonzero(other)
            ny,nx=reverse[:,by,bx]
            pix=np.r_[index,np.c_[ny,nx]]
            target=np.r_[nearest,np.c_[by,bx]]
            ids=drawn.triangle[pix[:,0],pix[:,1]]
            tri=faces[ids]
            residual = (target-pix)[:, ::-1].astype(float)
            size = np.linalg.norm(residual,axis=1)
            reliability = np.sqrt(np.minimum(1,4/np.maximum(size,1e-6)))
            rows = (basis[tri[:,0]]+basis[tri[:,1]]+basis[tri[:,2]])/3
            mid=posed[tri].mean(axis=1)
            deriv=[(camera.project(mid+axis*.01,SIZE)[:,:2]-camera.project(mid,SIZE)[:,:2])/.01
                   for axis in np.eye(3)]
            coords = np.stack(deriv,axis=2)
            prep=rows.tocoo()
            matrix=csr_matrix((np.concatenate([prep.data*coords[prep.row,j,k]*reliability[prep.row]
                         for j in range(2) for k in range(3)]),
                         (np.concatenate([prep.row*2+j for j in range(2) for k in range(3)]),
                          np.concatenate([prep.col*3+k for j in range(2) for k in range(3)]))),
                              shape=(len(pix)*2,dim*3))
            jac.append(matrix)
            targets.append((residual*reliability[:,None]).ravel())
        if not jac:
            break
        system=vstack([*jac,5*reg,2*prior],format='csr')
        result=lsqr(system,np.r_[*targets,np.zeros(reg.shape[0]+prior.shape[0])],iter_lim=85)
        delta=basis @ result[0].reshape(-1,3)
        update=p + .55*delta
        dist=np.linalg.norm(update-anchor,axis=1)
        p=anchor+(update-anchor)*np.minimum(1,1.8/np.maximum(dist,1e-9))[:,None]
        notes.append({'pixels':int(sum(len(x)//2 for x in targets)), 'solver_steps':int(result[2]),
                      'fit_residual_norm':float(result[3])})
    return p, notes


def iou(raster, p, faces, ref, rf):
    score=[]
    for yaw in CONFIG['holdout_yaw_deg']:
        cam=Camera(yaw,**CONFIG['main_camera_cm'])
        a=raster.draw(cam,p,faces,SIZE)
        b=raster.draw(cam,ref,rf,SIZE)
        score.append(float((a&b).sum()/(a|b).sum()))
    return score


def main(args):
    raster=Raster(args.raster)
    path=args.baseline/args.reference.stem
    with np.load(args.reference) as source:
        ref,rf,faces = [source[k] for k in ('reference','reference_faces','faces')]
    out = args.output / args.reference.stem
    out.mkdir(parents=True,exist_ok=True)
    cm=np.load(path/'calibrated/D0.npy')*10
    payload={'D0':cm,'reference':ref,'reference_faces':rf,'faces':faces}
    report={'study':{},'D0_heldout_iou':iou(raster,cm,faces,ref,rf)}
    for mode in ('calibrated','estimated'):
        folder=path/mode
        if not (folder/'D0.npy').exists():
            report[mode]={'unavailable':'Engine B did not complete'}
            continue
        start_mesh=np.load(folder/'D0.npy')*10
        sess=Session(folder/'project')
        body=load_project_body(sess.store)
        basis=NativeBasis(args.runtime,body)
        ids={photo.id:int(Path(photo.name).stem) for photo in sess.store.load().photos.photos}
        views,cameras,_=admit(body,basis,sess,ids,folder,mode=='estimated')
        names = [(view,cameras[view.id],resized(view.mask.astype('uint8'),SIZE).astype(bool)) for view in views]
        anchor_name=f'B_{mode}'
        payload[anchor_name]=start_mesh
        settings=[(f'P_{mode}_rgb', names)]
        if mode=='calibrated':
            oracle=[]
            for yaw in CONFIG['fit_yaw_deg']:
                cam=Camera(yaw,**CONFIG['main_camera_cm'])
                oracle.append((None,cam,raster.draw(cam,ref,rf,SIZE)))
            settings += [(f'P_oracle_{n}',oracle[:n]) for n in (1,2,4,8)]
            for field,value in [('yaw',8),('elevation',7),('dx',.025),('span',15),('distance',-110)]:
                settings.append((f'P_stress_{field}',[(v,replace(c,**{field:getattr(c,field)+value}),m)
                                                      for v,c,m in oracle[:4]]))
            # No predictor inference. Reuse G5's exact maps and local photographic
            # control on this identical calibrated M7 starting mesh.
            exact,_,_=make_maps(raster,start_mesh/10,faces,views,cameras,ref,rf,ids,
                                 Path('/nonexistent'),args.rgb/args.reference.stem,body,False)
            local, detail=refine(body,start_mesh/10,faces,views,cameras,exact,raster,photograph_only=True)
            payload['L0_replay']=local*10
            report['study']['L0_replay']=detail
        b,l=ffd(start_mesh,(5,8,5))
        gb,gl=graph(start_mesh,adjacency(start_mesh,faces),np.unique(faces),120)
        for name, observations in settings:
            for tag, matrix, regularizer in [('ffd',b,l),('graph',gb,gl)]:
                if name.startswith('P_stress') and tag=='graph':
                    continue
                begin=perf_counter()
                proposed,logs=warp(start_mesh,faces,body,raster,observations,matrix,regularizer)
                old=unit_normals(start_mesh,faces)
                frac=1.
                for frac in (1.,.75,.5,.25,.125,.0625,0.):
                    candidate=start_mesh+frac*(proposed-start_mesh)
                    try:
                        validate_rebind(body,candidate/10)
                        if ((old*unit_normals(candidate,faces)).sum(1)[np.unique(faces)]<0).any():
                            raise ValueError('vertex normal flipped')
                        break
                    except ValueError:
                        continue
                key=name+'_'+tag
                payload[key]=candidate
                report['study'][key]={'seconds':perf_counter()-begin,'pre_screen_fraction':frac,
                     'views':len(observations),'heldout_iou_candidate':iou(raster,candidate,faces,ref,rf),
                     'heldout_iou_start':iou(raster,start_mesh,faces,ref,rf),'curve':logs}
                print(args.reference.stem,key,frac,flush=True)
    np.savez_compressed(out/'proposals.npz',**payload)
    (out/'fit.json').write_text(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('runtime','reference','baseline','raster','rgb','output'):
        p.add_argument(key,type=Path)
    main(p.parse_args())
