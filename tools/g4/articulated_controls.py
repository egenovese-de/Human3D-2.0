"""Compare known, estimated, and ignored observation articulation."""
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

from benchmark import calibrated, load_json, make_view, sources
from evidence import sdf
from fitter import AnatomicalFitter, NativeBasis
from g1_benchmark import Engine, dump
from human3d.vision import _NativePoseLandmarker, estimate_world_yaw
from projection import Raster
from registration import FIT_SIZE, INDEX, Observation, Rig, anchor_projection_std, select_landmark_parity


def rgb_observation(folder, detector, cam):
    photo=folder/'rgb.png'
    evidence=detector.detect(photo,sha256(photo.read_bytes()).hexdigest())
    if len(evidence.candidates)!=1 or not evidence.masks or not evidence.masks[0]:
        return None
    points=evidence.candidates[0]
    xy=np.array([[points[i].x,points[i].y] for i in INDEX])*FIT_SIZE
    confidence=np.array([(points[i].visibility or 0)*(points[i].presence or 0) for i in INDEX])
    foreground=np.asarray(Image.open(BytesIO(evidence.masks[0])))>0
    mask=cv2.resize(foreground.astype('uint8'),(160,160),interpolation=cv2.INTER_NEAREST_EXACT)>0
    yaw=estimate_world_yaw(points,evidence.world_landmarks[0]) if evidence.world_landmarks else None
    ob=Observation(xy,confidence,mask,abs(sdf(mask))<=1,focal_px_prior=FIT_SIZE*cam.distance/cam.span,
                   signed_yaw_prior=-yaw if yaw is not None else None,capture_yaw_sector=round(cam.yaw/90)*90)
    return foreground,ob


def main(g2,g3,raster_path,model,out):
    cv2.setNumThreads(1)
    e=Engine()
    basis=NativeBasis(e,load_json(g2/'measurements/config.json'))
    detector=_NativePoseLandmarker(model,segmentation=True)
    raster=Raster(raster_path)
    neutral=Rig(e.body['rig'],basis.evaluate(basis.home))
    for case in ('A_high_mass','A_heldout_1'):
        files=g3/'articulated'/case
        registration=load_json(files/'registration.json')['views']
        refs=dict(np.load(g2/'geometry'/(case+'.npz')))
        faces=refs['faces']
        fitter=AnatomicalFitter(basis,raster,faces)
        folder=out/case
        folder.mkdir(exist_ok=True,parents=True)
        base=sources(g2,None,case)['calibrated_m6'][:2]
        modes={'MIXED_ORACLE_POSE':base.copy(),'MIXED_POSE_IGNORED':base.copy(),
               'MIXED_G3_POSE':base.copy()}
        camera_notes={}
        for key in ('near_articulated','far_articulated','cropped_occluded'):
            camera=calibrated(registration[key]['truth_camera'])
            rgba=rgb_observation(files/key,detector,camera)
            if rgba is None:
                camera_notes[key]={'status':'detector_abstention'}
                continue
            mask,obs=rgba
            truth=np.load(files/key/'truth.npz')
            excluded=cv2.resize((truth['states']==3).astype('uint8'),(384,384),
                                 interpolation=cv2.INTER_NEAREST_EXACT)>0
            pose=truth['pose_parameters']
            known=make_view(key,camera,mask,pose=pose,excluded=excluded)
            modes['MIXED_ORACLE_POSE'].append(known)
            modes['MIXED_POSE_IGNORED'].append(replace(known,pose=None))
            estimated=select_landmark_parity(neutral,obs,faces,raster,None)
            camera_notes[key]={'status':estimated['status']}
            if estimated['status']=='ok':
                notes=camera_notes[key]
                notes['yaw_estimated']=estimated['camera'].yaw
                notes['yaw_truth']=camera.yaw
                notes['parity']=estimated['detector_parity']
                notes['propagated_sigma_px']=float(np.median(anchor_projection_std(neutral,estimated)))
                modes['MIXED_G3_POSE'].append(make_view(key,estimated['camera'],mask,'external_sector',
                    pose=estimated['pose'],excluded=excluded,registration_sigma=notes['propagated_sigma_px'],
                    alternatives=tuple(estimated['alternatives'])))
        samples={k:refs[k] for k in ('reference','faces','reference_faces')}
        details={'registration':camera_notes,'fits':{}}
        for key,views in modes.items():
            rebind_safe,row=fitter.fit(views,budget=370)
            details['fits'][key]=row
            if rebind_safe is not None:
                samples[key]=rebind_safe
            print(case,key,row['status'],round(row.get('seconds',0),2),flush=True)
        first=base[0]
        expected,ref_result=fitter.fit(base,budget=160)
        replay,result=fitter.fit([*reversed(base),replace(first,key='zz-copy'),
                                  replace(first,key='zz-unresolved',camera_source='automatic')],budget=160)
        details['invariance']={'canonical_hash_equal':ref_result.get('canonical_sha256')==result.get('canonical_sha256'),
                               'mesh_equal':bool(np.array_equal(expected,replay)),'excluded':result['excluded']}
        dump(folder/'articulated.json',details)
        np.savez_compressed(folder/(case+'.npz'),**samples)
    detector.close()


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
