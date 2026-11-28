"""Coarse capture-sector, contour, and redundant-view ablations."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image

from benchmark import HELD_OUT, Z, g2_camera, measure, resize_mask
from evidence import edge, edge_distance, sdf
from g1_benchmark import Engine, dump
from human3d.vision import _NativePoseLandmarker, estimate_world_yaw
from projection import Raster
from registration import INDEX, FIT_SIZE, Observation, Rig, camera, deduplicate, select_landmark_parity


def refine(rig, observation, raster, faces, result):
    """Reproject contours while holding the selected articulation fixed."""
    cam, pose = result['camera'], result['pose']
    initial = np.r_[np.deg2rad([cam.yaw, cam.elevation, cam.roll]),
                    np.log([cam.span, cam.distance]), cam.dx, cam.dy]
    vertices, anchors = rig.mesh(pose), rig.anchors(pose)
    reference_edge = edge(observation.mask) & ~observation.excluded
    reference_distance = edge_distance(observation.mask)
    selected = result['used']
    xy, weight = observation.xy, observation.confidence
    if result.get('detector_parity') == 'swapped':
        order = [INDEX.index(i+1 if i%2 else i-1) for i in INDEX]
        xy, weight = xy[order], weight[order]

    def loss(parameters):
        candidate = camera(parameters, cam.perspective)
        mask = raster.draw(candidate, vertices, faces, len(observation.mask))
        boundary = edge(mask) & ~observation.excluded
        if not boundary.any() or not reference_edge.any():
            return 1000.
        contour = np.minimum(reference_distance[boundary], 12).mean()
        contour += np.minimum(edge_distance(mask)[reference_edge], 12).mean()
        errors = np.linalg.norm(candidate.project(anchors, FIT_SIZE)[selected, :2]-xy[selected], axis=1)
        anchor = np.average(np.minimum(errors, 40), weights=weight[selected])
        area = ((mask ^ observation.mask) & ~observation.excluded).sum()/max(1, observation.mask.sum())
        prior = np.linalg.norm((parameters-initial)/[.12,.12,.10,.08,.13,.035,.035])
        return float(contour+.32*anchor+2*area+.18*prior)

    params = initial.copy()
    first = best = loss(params)
    steps = np.array([.06,.05,.035,.035,.09 if not observation.focal_px_prior else 0.,.012,.012])
    for step_scale in (1., .5):
        for i,step in enumerate(steps):
            for sign in (-1,1):
                proposal = params.copy()
                proposal[i] += sign*step*step_scale
                value = loss(proposal)
                if value < best:
                    params, best = proposal, value
    return result | {'camera':camera(params, cam.perspective), 'pre_contour_loss':first, 'post_contour_loss':best}


def main(g2, output, model, library):
    cv2.setNumThreads(1)
    raster = Raster(library)
    engine = Engine()
    detector = _NativePoseLandmarker(model, segmentation=True)
    nominal = Rig(engine.body['rig'], engine.extended({})*10)
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for file in sorted((g2/'geometry').glob('A_*.npz')):
        case = file.stem
        arrays = np.load(file)
        ref = Rig(engine.body['rig'], arrays['reference'])
        faces = arrays['faces']
        candidates, sectors, refined = [], {}, {}
        for kind in ('0','45','90','180'):
            folder = g2/'evidence_maps'/case/kind
            photo = folder/'rgb.png'
            cam = g2_camera(json.loads((folder/'camera.json').read_text()))
            detected = detector.detect(photo, sha256(photo.read_bytes()).hexdigest())
            if len(detected.candidates) != 1 or not detected.masks or not detected.masks[0]:
                continue
            pts = detected.candidates[0]
            xy = np.array([[pts[i].x,pts[i].y] for i in INDEX])*FIT_SIZE
            trust = np.array([(pts[i].visibility or 0)*(pts[i].presence or 0) for i in INDEX])
            mask = resize_mask(np.asarray(Image.open(BytesIO(detected.masks[0])))>0,160)
            yaw = estimate_world_yaw(pts, detected.world_landmarks[0]) if detected.world_landmarks else None
            reliability = min((pts[i].visibility or 0)*(pts[i].presence or 0) for i in (0,2,5))
            hint = (pts[0].x*FIT_SIZE, pts[0].y*FIT_SIZE, reliability) if reliability>.75 else None
            obs = Observation(xy,trust,mask,abs(sdf(mask))<=1,signed_yaw_prior=-yaw if yaw is not None else None,
                              nose_hint=hint,capture_yaw_sector=round(cam.yaw/90)*90)
            fit = select_landmark_parity(nominal,obs,faces,raster,~HELD_OUT)
            if fit['status']!='ok':
                sectors[kind]=fit
                continue
            truth = raster.draw(cam,ref.vertices,faces,160)
            args = nominal,ref.anchors(Z),cam,truth,raster,faces
            sectors[kind] = measure(fit,*args)
            started = time.perf_counter()
            extra = refine(nominal,obs,raster,faces,fit)
            refined[kind] = measure(extra,*args) | {'seconds':time.perf_counter()-started,
                'pre_contour_loss':extra['pre_contour_loss'],'post_contour_loss':extra['post_contour_loss']}
            candidates.append(dict(id=kind,yaw=fit['camera'].yaw,mask=mask,weight=1/(1+fit['cost'])))
        front = next((v for v in candidates if v['id']=='0'), None)
        if front is not None:
            candidates += [front|{'id':'duplicate','weight':front['weight']*.9},
                           front|{'id':'shifted_copy','mask':np.roll(front['mask'],1,axis=1),'weight':front['weight']*.8}]
        kept, duplicates = deduplicate(candidates,shape_iou_min=.91)
        results[case] = dict(orientation_sector=sectors,sector_plus_contour=refined,
            duplicate_case=dict(input=[v['id'] for v in candidates],kept=[v['id'] for v in kept],suppressed=duplicates))
        print(case,{k:round(v['anchor_mean_px'],2) for k,v in refined.items()},flush=True)
    detector.close()
    dump(output/'orientation.json',results)


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
