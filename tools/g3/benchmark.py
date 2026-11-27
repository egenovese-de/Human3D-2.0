"""Controlled G3 registration experiments. Truth channels are isolated from RGB fits."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import platform
import resource
from time import perf_counter
import cv2
import numpy as np
from PIL import Image

from g1_benchmark import Engine, dump
from human3d.alignment import initialize_alignment
from human3d.native_rig import posed_segments, validate_rebind
from human3d.vision import _NativePoseLandmarker, estimate_world_yaw
from evidence import edge, sdf
from photographic import triangle_regions
from projection import Camera, Raster
from registration import (INDEX, TOKENS, FIT_SIZE, POSE_KEYS, Observation, Rig, angle_error,
                          solve, select_landmark_parity, anchor_projection_std, image_metadata)

HELD_OUT = np.array([idx in (15,16,27,28) for idx in INDEX])
Z = np.zeros(len(POSE_KEYS))


def resize_mask(mask,size):
    return cv2.resize(mask.astype('uint8'),(size,size),interpolation=cv2.INTER_NEAREST_EXACT).astype(bool)


def measure(result, reference, points, truth_camera, mask, raster, faces, output=None, regions=None, oracle_pose=None):
    if result['status']!='ok':
        return result
    cam,pose = result['camera'],result['pose']
    uv = cam.project(reference.anchors(pose),FIT_SIZE)[:,:2]
    truth_uv = truth_camera.project(points,FIT_SIZE)[:,:2]
    err = np.linalg.norm(uv-truth_uv,axis=1)
    pred = raster.draw(cam,reference.mesh(pose),faces,len(mask))
    region_scores = {}
    if regions is not None:
        for number in np.unique(regions):
            if number==0:
                continue
            support = regions==number
            region_scores[str(number)] = float((pred&support).sum()/support.sum())
    if output is not None:
        np.savez_compressed(output, predicted=pred, reference=mask, prediction_xy=uv,
                            reference_xy=truth_uv, posed_cm=reference.mesh(pose), faces=faces)
    return {'status':'ok','yaw_error_deg':abs(angle_error(cam.yaw,truth_camera.yaw)),
            'elevation_error_deg':abs(cam.elevation-truth_camera.elevation),
            'roll_error_deg':abs(angle_error(cam.roll,truth_camera.roll)),
            'scale_error_percent':100*abs(truth_camera.span/cam.span-1),
            'distance_error_percent':100*abs(cam.distance/truth_camera.distance-1) if cam.perspective and truth_camera.perspective else None,
            'principal_offset_error_px':float(np.linalg.norm([cam.dx-truth_camera.dx,cam.dy-truth_camera.dy])*FIT_SIZE),
            'anchor_mean_px':float(err.mean()),'heldout_mean_px':float(err[HELD_OUT].mean()),
            'train_mean_px':float(err[result['used']].mean()),
            'endpoint_anchors_heldout':bool(not np.any(result['used'] & HELD_OUT)),
            'mask_iou':float((mask&pred).sum()/max(1,(mask|pred).sum())),
            'region_foreground_recall':region_scores,'anchor_error_px':dict(zip(map(str,INDEX),err.tolist())),
            'pose_parameter_rms_deg':float(np.degrees(np.sqrt(np.mean((pose-oracle_pose)**2)))) if oracle_pose is not None else None,
            'covariance':result['covariance'].tolist(),'effective_data_rank':result['effective_data_rank'],
            'ambiguity_gap':result['ambiguity_gap'],'alternatives':result['alternatives'],'scale_certificate':result['scale'],
            'estimated_camera':cam.manifest(FIT_SIZE),
            'camera_only_anchor_std_px':anchor_projection_std(reference,result).tolist(),
            'detector_parity':result.get('detector_parity'),'parity_gap':result.get('parity_gap'),
            'parity_alternatives':result.get('parity_alternatives')}


def m6_baseline(engine, detection, truth_rig, truth_pose, cam, truth_mask, faces, raster):
    try:
        alignment = initialize_alignment(engine.body,detection,0,refine=True)
    except (ValueError,IndexError) as exc:
        return dict(status='abstained',reason=str(exc))
    rig = engine.body['rig']
    segs = posed_segments(rig,{name:np.asarray(point) for name,point in rig['joints'].items()},alignment)
    uv = np.array([[z.real,z.imag] for idx in INDEX for z in (alignment.camera.project(segs[TOKENS[idx]][0]),)])
    expected = cam.project(truth_rig.anchors(truth_pose),FIT_SIZE)[:,:2]
    errors = np.linalg.norm(uv-expected,axis=1)
    return dict(status='ok',yaw_error_deg=abs(angle_error(-alignment.camera.yaw_degrees,cam.yaw)),
                anchor_mean_px=float(errors.mean()),heldout_mean_px=float(errors[HELD_OUT].mean()),
                heldout_used_by_m6=True)


def evaluate(existing, rgb_path, result_dir, reference, nominal, engine, camera, truth_pose, faces,
             raster, detector, focal_prior, crop=False):
    size = 160
    posed = reference.mesh(truth_pose)
    mask,_,ids = raster.draw(camera,posed,faces,size,True)
    labels = triangle_regions(engine,faces)
    regions = np.zeros_like(ids,np.uint8)
    regions[mask] = labels[ids[mask]]
    points = reference.anchors(truth_pose)
    xy = camera.project(points,FIT_SIZE)[:,:2]
    visible = (xy>0).all(axis=1)&(xy<FIT_SIZE).all(axis=1)
    excluded = np.zeros_like(mask)
    if crop:
        excluded[115:,:] = True
        excluded[55:94,66:91] = True
        pix = np.clip(np.floor(xy/FIT_SIZE*size).astype(int),0,size-1)
        visible &= ~excluded[pix[:,1],pix[:,0]]
    occluded = excluded.copy()
    floor = sdf(mask)
    excluded |= abs(floor)<=1
    oracle = Observation(xy,visible.astype(float),mask,excluded,focal_px_prior=focal_prior,
                         scale_cm_per_model_unit=1 if focal_prior else None)
    rgb_ob = None
    record = dict(source=existing,truth_camera=camera.manifest(FIT_SIZE),
                  usable_oracle_anchors=int(visible.sum()),excluded_area_fraction=float(excluded.mean()),fits={})
    if rgb_path is not None:
        record['image_metadata'] = image_metadata(rgb_path)
        detected = detector.detect(rgb_path,sha256(rgb_path.read_bytes()).hexdigest())
        record['candidate_count'] = len(detected.candidates)
        if len(detected.candidates)==1 and detected.masks and detected.masks[0]:
            landmarks = detected.candidates[0]
            samples = np.array([[landmarks[i].x,landmarks[i].y] for i in INDEX])*FIT_SIZE
            reliability = np.array([(landmarks[i].visibility or 0)*(landmarks[i].presence or 0) for i in INDEX])
            oriented = detected.world_landmarks[0] if detected.world_landmarks else ()
            yaw = estimate_world_yaw(landmarks,oriented)
            detected_mask = resize_mask(np.asarray(Image.open(BytesIO(detected.masks[0])))>0,size)
            # Occluder annotations are an explicit separate input. RGB-only G3 has no access here.
            boundary = abs(sdf(detected_mask))<=1
            face_quality = min((landmarks[i].visibility or 0)*(landmarks[i].presence or 0) for i in (0,2,5))
            nose = (landmarks[0].x*FIT_SIZE,landmarks[0].y*FIT_SIZE,face_quality) if face_quality>.75 else None
            rgb_ob = Observation(samples,reliability,detected_mask,boundary,
                                 focal_px_prior=focal_prior, signed_yaw_prior=-yaw if yaw is not None else None,nose_hint=nose)
            record['m6_baseline'] = m6_baseline(engine,detected,reference,truth_pose,camera,mask,faces,raster)
    variants = [
        ('oracle_camera_and_fit_pose',reference,oracle,True,True,camera,~HELD_OUT),
        ('oracle_anchors_perspective',reference,oracle,True,True,None,~HELD_OUT),
        ('oracle_anchors_weak',reference,oracle,True,False,None,~HELD_OUT),
    ]
    if rgb_ob is not None:
        variants += [('rgb_known_shape',reference,rgb_ob,True,True,None,~HELD_OUT),
                     ('rgb_nominal_shape',nominal,rgb_ob,True,True,None,~HELD_OUT)]
    if rgb_ob is not None and not existing:
        from dataclasses import replace
        # Oracle admission of a coarse capture sector, not an automatic orientation estimate.
        approximate_sector=round(camera.yaw/90)*90
        variants.append(('rgb_capture_sector_control',nominal,replace(rgb_ob,capture_yaw_sector=approximate_sector),
                         True,True,None,~HELD_OUT))
    if not existing:
        variants.append(('oracle_camera_all_anchors',reference,oracle,True,True,camera,None))
    if rgb_ob is None:
        variants += [('oracle_pose_ignored',reference,oracle,False,True,None,~HELD_OUT)]
    if crop:
        corrupted = xy.copy()
        corrupted[~visible] += np.array([35.,-22.])
        variants.append(('corrupt_hidden_anchors_trusted',reference,Observation(corrupted,np.ones(len(INDEX)),
                         mask&~excluded,np.zeros_like(mask),focal_px_prior=focal_prior),True,True,None,~HELD_OUT))
        if rgb_ob is not None:
            from dataclasses import replace
            locations=np.clip(np.floor(rgb_ob.xy/FIT_SIZE*size).astype(int),0,size-1)
            trust=rgb_ob.confidence.copy()
            trust[occluded[locations[:,1],locations[:,0]]]=0.
            variants.append(('rgb_annotated_occlusion',nominal,replace(rgb_ob,excluded=rgb_ob.excluded|occluded,
                             confidence=trust),True,True,None,~HELD_OUT))
    for name,rig,obs,art,persp,known,indices in variants:
        start = perf_counter()
        fn = select_landmark_parity if name.startswith('rgb_') else solve
        fit = fn(rig,obs,faces,raster,indices=indices,articulate=art,perspective=persp,calibrated_camera=known)
        if fit['status']=='ok':
            # Project true points for both known and nominal anatomy while keeping predicted geometry on its own rig.
            row = measure(fit,rig,points,camera,mask,raster,faces,result_dir/(name+'.npz')
                          if name in ('rgb_nominal_shape','oracle_anchors_perspective') else None,regions,truth_pose)
        else:
            row = fit
        row['seconds'] = perf_counter()-start
        record['fits'][name] = row
    state=np.where(mask,1,2).astype(np.uint8)
    state[abs(floor)<=1]=4
    state[occluded]=3
    np.savez_compressed(result_dir/'truth.npz',states=state,rest_cm=reference.vertices,reference_pose_cm=posed,faces=faces,
                        mask=mask,regions=regions,excluded=excluded,anchors_xy=xy,pose_parameters=truth_pose)
    return record


def g2_camera(data):
    keys=('yaw','span','center_y','elevation','distance','perspective','roll','dx','dy')
    return Camera(**{key:data[key] for key in keys})


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--g2',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--raster',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cases',nargs='*')
    p.add_argument('--quick',action='store_true')
    a=p.parse_args()
    cv2.setNumThreads(1)
    engine=Engine()
    raster=Raster(a.raster)
    model=_NativePoseLandmarker(a.model,segmentation=True)
    nominal=Rig(engine.body['rig'],engine.extended({})*10)
    for file in sorted((a.g2/'geometry').glob('A_*.npz')):
        case=file.stem
        if a.cases and case not in a.cases:
            continue
        arrays=np.load(file)
        ref=Rig(engine.body['rig'],arrays['reference'])
        faces=arrays['faces']
        folder=a.output/case
        folder.mkdir(parents=True,exist_ok=True)
        try:
            validate_rebind(engine.body,ref.vertices/10)
            rebind='PASS'
        except ValueError as exc:
            rebind=str(exc)
        record=dict(canonical_sha256=sha256(ref.vertices.tobytes()).hexdigest(),rebind=rebind,views={})
        for view in ('0','45','90','180','perspective') if not a.quick else ('0',):
            source=a.g2/'evidence_maps'/case/view
            if not (source/'camera.json').is_file():
                continue
            cam=g2_camera(json.loads((source/'camera.json').read_text()))
            dst=folder/view
            dst.mkdir(exist_ok=True)
            record['views'][view] = evaluate(True,source/'rgb.png',dst,ref,nominal,engine,cam,Z,faces,raster,model,None)
            print(case,view,{k:round(v['anchor_mean_px'],2) for k,v in record['views'][view]['fits'].items() if v['status']=='ok'},flush=True)
        for name,cam,parameters,crop in [
            ('near_articulated',Camera(52,span=232,elevation=13,distance=300,perspective=True,roll=6,dx=.035,dy=-.04),
                [.34,.28,.31,-.42,-.28,.17,.23,-.25,.15,.15,-.14,.31,-.12,.29,.10,-.34],False),
            ('far_articulated',Camera(-73,span=213,elevation=-7,distance=680,perspective=True,roll=-4,dx=-.035,dy=.02),
                [-.26,.20,.19,.30,.21,-.16,-.36,.13,.10,-.18,-.20,.15,.13,.18,-.22,-.10],False),
            ('cropped_occluded',Camera(30,span=195,elevation=10,distance=305,perspective=True,roll=4,dy=.055),
                [.34,.28,.31,-.42,-.28,.17,.23,-.25,.15,.15,-.14,.31,-.12,.29,.10,-.34],True),
        ]:
            if a.quick and name!='near_articulated':
                continue
            dst=folder/name
            dst.mkdir(exist_ok=True)
            record['views'][name] = evaluate(False,None,dst,ref,nominal,engine,cam,np.asarray(parameters),faces,raster,model,
                                             FIT_SIZE*cam.distance/cam.span,crop=crop)
            print(case,name,{k:round(v['anchor_mean_px'],2) for k,v in record['views'][name]['fits'].items() if v['status']=='ok'},flush=True)
        record['canonical_unchanged']=record['canonical_sha256']==sha256(ref.vertices.tobytes()).hexdigest()
        dump(folder/'registration.json',record)
    model.close()
    dump(a.output/'runtime.json',dict(platform=platform.platform(),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    main()
