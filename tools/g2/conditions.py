"""Clothing, landmark region, and pose controls on one reference anatomy."""
from pathlib import Path
import json
import sys
import cv2
import numpy as np
from PIL import Image
from g1_benchmark import Engine, dump
from human3d.alignment import Alignment, Camera as M6Camera
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from evidence import mask_metrics, profile
from photographic import ANGLES, SIZE, compile_view, coordinate_fit, triangle_regions
from projection import Camera, Raster


def garment(v, ease):
    q = v.copy()
    # Regional offset is an outer-envelope sensitivity control, with no cloth simulation.
    y = np.abs(q[:,1]-25)
    x = np.abs(q[:,0])
    amount = np.clip((32-y)/12,0,1)*np.clip((37-x)/9,0,1)*ease
    q[:,0] += np.sign(q[:,0])*amount*.55
    q[:,2] += np.sign(q[:,2]-1)*amount
    return q


def arm_pose(e,v):
    rig = e.body['rig']
    camera = M6Camera(0,20,0j,1)
    alignment = Alignment(camera,0.,{'upperarm01.L':1.9,'lowerarm01.L':2.1})
    transforms = pose_transforms(rig,rebind_joints(rig,v/10),alignment)
    return np.asarray(skin_vertices(v/10,rig['skin'],transforms))*10


def main(reference, config, out, library):
    out.mkdir(exist_ok=True,parents=True)
    a = np.load(reference)
    e = Engine()
    raster = Raster(library)
    settings = json.loads(config.read_text())
    names = settings['g1_fields']
    initial = np.asarray(settings['g1_initial'])
    bounds = np.asarray(settings['g1_bounds'])
    ref,faces = a['reference'],a['faces']
    native = lambda values:e.extended(dict(zip(names,values)))*10
    posed = lambda values:arm_pose(e,native(values))
    regions = triangle_regions(e,faces)
    masks,results = {},{}
    for camera in [Camera(angle) for angle in ANGLES]:
        name = str(camera.yaw)
        true,_,ids = raster.draw(camera,ref,faces,384,True)
        variants = dict(body=true,tight=raster.draw(camera,garment(ref,1.2),faces,384),
                        loose=raster.draw(camera,garment(ref,5.5),faces,384),
                        posed=raster.draw(camera,arm_pose(e,ref),faces,384))
        masks[name] = variants
        results[name] = {k:mask_metrics(pred,true) for k,pred in variants.items() if k!='body'}
        labels = np.zeros_like(ids)
        labels[true] = regions[ids[true]]
        results[name]['regional_projection'] = {str(r):int((labels==r).sum()) for r in range(1,17)}
        results[name]['torso_profile_width_delta_px'] = {
            k:float(np.mean(np.abs(profile(p,np.arange(93,180))[:,2]-profile(true,np.arange(93,180))[:,2])))
            for k,p in variants.items() if k!='body'}
        comparison = np.zeros((*true.shape,3),np.uint8)
        comparison[variants['loose']] = [230,164,90]
        comparison[variants['tight']] = [134,164,206]
        comparison[true] = [65,133,140]
        Image.fromarray(comparison).save(out/f'clothing-{name}.png')
    meshes = dict(reference=ref,faces=faces,reference_faces=faces)
    for key,source,kind,model in [('body_control','body','dense',native),('loose_as_body','loose','dense',native),
                                  ('loose_outer_bound','loose','outer',native),
                                  ('pose_mismatch','posed','dense',native),('pose_calibrated','posed','dense',posed)]:
        obs = [compile_view({'camera':Camera(angle),'mask':{'input':masks[str(angle)][source]}},'input') for angle in ANGLES]
        if kind=='outer':
            middle = (np.indices((SIZE,SIZE))[0]>=32)&(np.indices((SIZE,SIZE))[0]<=73)
            for o in obs:
                o['hidden'] = middle
            def penalty(pred,depth,ids,o,v):
                return .25*float((pred&o['nbg']&middle).sum()/o['size'])
        else:
            penalty = None
        output,results[key] = coordinate_fit(model,bounds,initial,faces,obs,'dense',raster,extra=penalty,
                                               steps=(.23,.11,.05))
        # The fitted controls always describe the neutral body.
        meshes[key] = native(results[key]['values'])
        print(key,results[key]['seconds'],flush=True)
    np.savez_compressed(out/'conditions.npz',**meshes)
    dump(out/'conditions.json',results)


if __name__=='__main__':
    cv2.setNumThreads(1)
    main(*map(Path,sys.argv[1:]))
