"""Isolate the anatomical value of exact visible same-topology correspondence."""
from pathlib import Path
import json
import sys
import numpy as np
from g1_benchmark import Engine, dump
from photographic import ANGLES, SIZE, compile_view, coordinate_fit
from projection import Camera, Raster


def samples_from_visibility(camera, vertices, triangles, raster):
    fg,_,ids = raster.draw(camera,vertices,triangles,384,True)
    yy,xx = np.where(fg)
    keep = np.arange(len(xx))[::90]
    yy,xx = yy[keep],xx[keep]
    corners = triangles[ids[yy,xx]]
    xy = camera.project(vertices,384)[corners,:2]
    first,second = xy[:,1]-xy[:,0],xy[:,2]-xy[:,0]
    offset = np.c_[xx+.5,yy+.5]-xy[:,0]
    det = first[:,0]*second[:,1]-first[:,1]*second[:,0]
    v = (offset[:,0]*second[:,1]-offset[:,1]*second[:,0])/det
    w = (first[:,0]*offset[:,1]-first[:,1]*offset[:,0])/det
    return corners,np.c_[1-v-w,v,w],np.c_[xx+.5,yy+.5]/384*SIZE


def counterpart(obs,vertices):
    points = np.sum(vertices[obs['indices']]*obs['weights'][...,None],axis=1)
    return obs['camera'].project(points,SIZE)[:,:2]


def main(refs, config, out, library):
    out.mkdir(exist_ok=True,parents=True)
    e=Engine()
    raster=Raster(library)
    settings=json.loads(config.read_text())
    names=settings['g1_fields']
    initial=np.asarray(settings['g1_initial'])
    bounds=np.asarray(settings['g1_bounds'])
    native=lambda x:e.extended(dict(zip(names,x)))*10
    output={}
    for case in ('A_high_mass','A_heldout_1'):
        a=np.load(refs/(case+'.npz'))
        ref,faces=a['reference'],a['faces']
        observations=[]
        for angle in ANGLES:
            camera=Camera(angle)
            view=compile_view({'camera':camera,'mask':{'truth':raster.draw(camera,ref,faces,384)}},'truth')
            view['indices'],view['weights'],view['target_px']=samples_from_visibility(camera,ref,faces,raster)
            observations.append(view)
        def extra(pred,depth,ids,obs,vertices):
            residual=np.linalg.norm(counterpart(obs,vertices)-obs['target_px'],axis=1)
            return .22*float(np.minimum(residual,12).mean()/5)
        meshes=dict(reference=ref,reference_faces=faces,faces=faces)
        row={}
        for key,penalty in [('matched_oracle_silhouette',None),('oracle_correspondence',extra)]:
            meshes[key],row[key]=coordinate_fit(native,bounds,initial,faces,observations,'dense',raster,extra=penalty)
        row['samples_per_view']=[len(obs['indices']) for obs in observations]
        row['identity_reprojection_max_px']=max(float(np.linalg.norm(counterpart(o,ref)-o['target_px'],axis=1).max()) for o in observations)
        dump(out/(case+'.json'),row)
        np.savez_compressed(out/(case+'.npz'),**meshes)
        output[case]=row
        print(case,row['samples_per_view'],flush=True)


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
