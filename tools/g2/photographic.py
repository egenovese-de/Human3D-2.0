"""G2 fixed-camera photographic benchmark. Measurements and fit inputs are separated."""
import argparse
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import platform
import resource
import time
from importlib.metadata import version

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from g1_benchmark import Engine, dump, measurements, triangulate, summary
from human3d.alignment import initialize_alignment, TORSO, LIMBS
from human3d.frozen_body import morph_controls
from human3d.native_rig import validate_rebind
from human3d.proportions import length_controls
from human3d.regional_morphs import regional_controls
from human3d.vision import _NativePoseLandmarker
from evidence import State, edge, edge_distance, gaps, mask_metrics, profile, rgb_grabcut, rgb_uniform, sdf, uncertainty
from projection import Camera, Raster

ANGLES = [0, 90, 180, 45]
SIZE = 144
REGIONS = ['head','neck','torso','pelvis','left_upper_arm','right_upper_arm','left_forearm',
           'right_forearm','left_hand','right_hand','left_thigh','right_thigh','left_lower_leg',
           'right_lower_leg','left_foot','right_foot']
REGION_BONES = ['head','neck','spine','pelvis','upperarm','upperarm','lowerarm','lowerarm',
                'hand wrist finger','hand wrist finger','upperleg','upperleg','lowerleg','lowerleg','foot toe','foot toe']
ANCHORS = TORSO | {last: next_bone for next_bone,(last,_) in LIMBS.items() if last in (13,14,15,16,25,26,27,28)}


def rgb_image(rgba, variant):
    y,x = np.indices(rgba.shape[:2])
    bg = np.broadcast_to([215,222,231],(*y.shape,3)).copy()
    if variant == 'background':
        bg = np.uint8(np.clip(bg + (36*np.sin(x/11)+22*np.cos(y/17))[...,None],0,255))
    alpha = rgba[:,:,3:4]/255
    rgb = (rgba[:,:,:3]*alpha+bg*(1-alpha)).astype(np.uint8)
    hidden = np.zeros_like(y,dtype=bool)
    if variant == 'occluded':
        hidden = (x>160)&(x<234)&(y>140)&(y<254)
        rgb[hidden] = [54,106,149]
    elif variant == 'dark':
        rgb = (rgb*.45).astype(np.uint8)
    elif variant == 'low_resolution':
        rgb = cv2.resize(cv2.resize(rgb,(128,128),interpolation=cv2.INTER_AREA),(384,384))
    elif variant == 'cropped':
        hidden = y > 294
        rgb[hidden] = [215,222,231]
    return rgb,hidden


def save_png(path, array):
    Image.fromarray(array).save(path)


def resize(mask):
    return cv2.resize(mask.astype(np.uint8),(SIZE,SIZE),interpolation=cv2.INTER_NEAREST_EXACT).astype(bool)


def anchor_points(engine,v):
    rig = engine.body['rig']
    return {i: v[rig['joint_vertices'][rig['bones'][name]['head']]].mean(0)
            for i,name in ANCHORS.items()}


def triangle_regions(engine, faces):
    categories = []
    for i,bases in enumerate(REGION_BONES):
        side = '.L' if REGIONS[i].startswith('left') else '.R' if REGIONS[i].startswith('right') else None
        categories.append([name for name in engine.body['rig']['bones']
                           if any(name.startswith(base) for base in bases.split()) and (side is None or name.endswith(side))])
    names = {name:i for i,bones in enumerate(categories) for name in bones}
    weights = np.zeros((len(engine.base),len(REGIONS)))
    for index,skin in enumerate(engine.body['rig']['skin']):
        for name,w in skin.items():
            if name in names:
                weights[int(index),names[name]] += w
    return 1+np.argmax(weights[faces].sum(axis=1),axis=1)


def extract(case, route, available, raster, detector, engine):
    case_path = available['root']
    stem = route['view']
    key = route['id']
    cam = route['camera']
    rgba = np.array(Image.open(case_path/(stem+'.png')).convert('RGBA'))
    rgb,hidden = rgb_image(rgba,route['variant'])
    folder = available['maps']/key
    folder.mkdir(parents=True,exist_ok=True)
    image = folder/'rgb.png'
    save_png(image,rgb)
    reference, faces = available['reference'], available['reference_faces']
    truth,depth,ids = raster.draw(cam,reference,faces,384,True)
    alpha_gt = rgba[:,:,3] >= 128
    px = cam.project(reference,384)
    normals = np.cross(reference[faces[:,1]]-reference[faces[:,0]],reference[faces[:,2]]-reference[faces[:,0]])
    normals /= np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    normal_map = np.zeros((*truth.shape,3),np.float32)
    normal_map[truth] = normals[ids[truth]]@cam.axes().T
    region_map = np.zeros_like(ids,dtype=np.uint8)
    if available['region_labels'] is not None:
        region_map[truth] = available['region_labels'][ids[truth]]
    digest = sha256(image.read_bytes()).hexdigest()
    started = time.perf_counter()
    detection = detector.detect(image,digest)
    detector_seconds = time.perf_counter()-started
    native = np.zeros_like(truth)
    if len(detection.candidates)==1 and detection.masks and detection.masks[0] is not None:
        native = np.asarray(Image.open(BytesIO(detection.masks[0]))) == 255
    t = time.perf_counter()
    keyed = rgb_uniform(rgb)
    keyed_seconds = time.perf_counter()-t
    t = time.perf_counter()
    refined = rgb_grabcut(rgb,native)
    refined_seconds = time.perf_counter()-t
    valid = ~hidden
    visible = truth & valid
    records = {'M6':native,'rgb_uniform':keyed,'M6_grabcut':refined}
    record = {name:mask_metrics(pred&valid,visible) for name,pred in records.items()}
    record['seconds'] = {'M6':detector_seconds,'rgb_uniform':keyed_seconds,'M6_grabcut':refined_seconds}
    record['raster_to_blender'] = mask_metrics(truth,alpha_gt)
    record['candidate_count'] = len(detection.candidates)
    record['suitability'] = vars(detection.suitability(0)) if len(detection.candidates)==1 else None
    record['profile_mae_px'] = {name:float(np.mean(abs(profile(pred&valid,np.arange(384))[...,2]-
                                                           profile(visible,np.arange(384))[...,2]))) for name,pred in records.items()}
    landmarks = np.empty((0,4))
    landmarks_gt = {}
    if len(detection.candidates)==1:
        landmarks = np.array([(p.x*384,p.y*384,p.visibility,p.presence) for p in detection.candidates[0]])
        if case.startswith('A_'):
            anchors = anchor_points(engine,reference)
            landmarks_gt = {i:cam.project(np.asarray([p]),384)[0,:2] for i,p in anchors.items()}
            record['landmarks'] = [{'index':i,'distance_px':float(np.linalg.norm(landmarks[i,:2]-xy)),
                                    'confidence':float(landmarks[i,2]*landmarks[i,3]),
                                    'admitted':bool(detection.visible_pose(0)[i].observed)}
                                   for i,xy in landmarks_gt.items()]
        try:
            a = initialize_alignment(engine.body,detection,0,refine=True)
            record['M6_alignment'] = {'yaw_degrees':a.camera.yaw_degrees,'roll_degrees':float(np.angle(a.camera.similarity,deg=True)),
                                     'px_per_dm':abs(a.camera.similarity),'torso_residual_px':a.torso_rms_pixels,
                                     'pose_segment_count':len(a.limb_angles)}
        except ValueError as exc:
            record['M6_alignment_error'] = str(exc)
    proposed = uncertainty(keyed,key,'RGB border key',band=1.5)
    oracle_hidden = uncertainty(keyed,key,'RGB border key + oracle occluder annotation',band=1.5,hidden=hidden)
    save_png(folder/'M6_mask.png',native.astype(np.uint8)*255)
    save_png(folder/'rgb_mask.png',keyed.astype(np.uint8)*255)
    save_png(folder/'negative_space.png',(gaps(keyed)&(proposed.state==State.BACKGROUND)).astype(np.uint8)*255)
    legend = np.array([[0,0,0],[118,188,172],[48,70,96],[159,107,180],[239,182,83]],dtype=np.uint8)
    save_png(folder/'evidence_states.png',legend[oracle_hidden.state])
    overlay = rgb.copy()
    overlay[keyed&~truth] = [232,90,79]
    overlay[truth&~keyed] = [43,170,245]
    overlay[hidden] = [133,88,163]
    save_png(folder/'mask_error.png',overlay)
    np.savez_compressed(folder/'estimated.npz',mask_m6=native,mask_rgb=keyed,mask_refined=refined,
                        uncertainty_rgb=proposed.state,confidence_rgb=proposed.confidence,
                        signed_distance_px=sdf(keyed),landmarks_px=landmarks,
                        profiles_px=profile(keyed,np.arange(384)))
    region_color = np.zeros((*truth.shape,3),np.uint8)
    rng = np.random.default_rng(782)
    region_color[truth] = np.r_[np.zeros((1,3),dtype=np.uint8),rng.integers(35,245,(len(REGIONS),3),dtype=np.uint8)][region_map[truth]]
    save_png(folder/'oracle_regions.png',region_color)
    depth_preview = np.zeros(truth.shape,np.uint8)
    depth_preview[truth] = (40+215*(depth[truth].max()-depth[truth])/max(1e-5,np.ptp(depth[truth]))).astype(np.uint8)
    save_png(folder/'oracle_depth.png',depth_preview)
    overlay_landmarks = rgb.copy()
    for x,y,*_ in landmarks:
        if np.isfinite(x+y):
            cv2.circle(overlay_landmarks,(round(x),round(y)),2,(242,209,85),-1)
    save_png(folder/'landmarks.png',overlay_landmarks)
    np.savez_compressed(folder/'oracle.npz',visible=visible,body=truth,occluded=hidden,
                        depth_cm=depth,normals_camera=normal_map,triangle_index=ids,region=region_map,
                        anchor_id=np.array(list(landmarks_gt)),anchors_px=np.array(list(landmarks_gt.values())))
    dump(folder/'camera.json',cam.manifest(384))
    return record, {'camera':cam,'key':key,'mask':{'m6':native,'rgb':keyed,'truth':truth},
                    'hidden':hidden,'detection':detection,'regions':region_map,'rgb':rgb}


def calibration(case, input_path, root, maps, detector, e, raster):
    arrays = dict(np.load(input_path))
    refs = arrays['reference'],arrays['reference_faces']
    available = dict(root=root,maps=maps,reference=refs[0],reference_faces=refs[1],
                     region_labels=triangle_regions(e,refs[1]) if case.startswith('A_') else None)
    routes = [dict(id=str(a),view=str(a),camera=Camera(a),variant='plain') for a in ANGLES]
    if case in ('A_high_mass','A_heldout_1','B_female'):
        routes.extend(dict(id=name,view='0',camera=Camera(0),variant=name)
                      for name in ['background','occluded','cropped','dark','low_resolution'])
    if (root/'perspective.png').exists():
        routes.append(dict(id='perspective',view='perspective',
                           camera=Camera(35,elevation=12,distance=260,perspective=True),variant='plain'))
    measures,views = {},{}
    for route in routes:
        k = route['id']
        measures[k],views[k] = extract(case,route,available,raster,detector,e)
    return arrays,measures,views


def compile_view(item, source, occlusion=False, camera=None, weight=1., mask=None):
    target = resize(item['mask'][source] if mask is None else mask)
    hidden = resize(item['hidden']) if occlusion else np.zeros_like(target)
    clean = (sdf(target) > 1) & ~hidden
    positive = target & ~hidden
    region = cv2.resize(item.get('regions',np.zeros((384,384),np.uint8)),(SIZE,SIZE),interpolation=cv2.INTER_NEAREST_EXACT)
    rows = np.arange(12,SIZE-12,2)
    return dict(camera=camera or item['camera'], target=target, positive=positive, nbg=clean,
                hidden=hidden, weight=weight, gap=gaps(target)&clean, region=region, rows=rows,
                distance=edge_distance(target), profile=profile(target,rows),
                edge=edge(target), size=max(1,int(target.sum())))


def score(pred, obs, mode, labels=None):
    gt, hidden = obs['target'],obs['hidden']
    union = np.count_nonzero((pred|gt)&~hidden)
    iou_loss = 1-np.count_nonzero(pred&gt&~hidden)/max(1,union)
    if mode=='iou':
        return iou_loss
    fp = np.count_nonzero(pred&obs['nbg'])
    fn = np.count_nonzero(~pred&obs['positive'])
    if mode=='signed':
        return (fp+fn)/obs['size']
    boundary = edge(pred)&~hidden
    a = obs['distance'][boundary]
    b = edge_distance(pred)[obs['edge']&~hidden] if boundary.any() else np.array([SIZE])
    chamfer = (np.minimum(a,18).mean() if a.size else 18) + (np.minimum(b,18).mean() if b.size else 18)
    if mode=='chamfer':
        return chamfer/20+.12*iou_loss
    if mode=='sdf':
        signed_gt = sdf(gt)
        signed_pred = sdf(pred)
        support = (np.minimum(abs(signed_gt),abs(signed_pred))<8)&~hidden
        return float(np.abs(np.clip(signed_pred,-8,8)-np.clip(signed_gt,-8,8))[support].mean()/8)
    gap = np.count_nonzero(pred&obs['gap'])/max(1,obs['size'])
    if mode=='gap':
        return chamfer/20+.12*(fp+fn)/obs['size']+.5*gap
    use = ~hidden.any(axis=1)[obs['rows']]
    prof = profile(pred,obs['rows'])
    if mode=='sparse':
        use &= np.arange(len(use))%10==0
    p = np.abs(prof[use]-obs['profile'][use]).mean()/20 if use.any() else 0
    value = chamfer/20+.11*(fp+fn)/obs['size']+.35*gap+.4*p
    if mode=='region' and labels is not None:
        inside = (obs['region']>0)&~hidden
        value += .3 * np.mean(labels[inside]!=obs['region'][inside]) if inside.any() else 0
    if mode=='hull':
        # Visibility-aware regional exclusion on the intersection of registered silhouette cones.
        # The 3-D hull ablation is computed separately by the volumetric experiment.
        value += .18*fp/obs['size']
    return value


def coordinate_fit(model, bounds, default, faces, observations, mode, raster, *, order=None, steps=(.23,.11,.05,.022), robust=False, region=None, extra=None):
    start = time.perf_counter()
    calls = 0
    def objective(values):
        nonlocal calls
        calls += 1
        vertices = model(values)
        terms = []
        for obs in observations:
            if mode == 'region' and region is not None or extra is not None:
                pred,depth,ids = raster.draw(obs['camera'],vertices,faces,SIZE,True)
                labels = np.zeros_like(ids)
                if region is not None:
                    labels[pred] = region[ids[pred]]
            else:
                pred = raster.draw(obs['camera'],vertices,faces,SIZE)
                labels = None
            penalty = extra(pred,depth,ids,obs,vertices) if extra is not None else 0.
            terms.append(score(pred,obs,mode,labels)+penalty)
        terms = np.array(terms)
        weights = np.array([ob['weight'] for ob in observations])
        if robust:
            terms = .16*np.log1p(terms/.16)
        return float(np.average(terms,weights=weights)+.0002*np.mean(values**2))
    values = default.copy()
    old = best = objective(values)
    order = range(len(values)) if order is None else order
    trajectory = [old]
    for step in steps:
        for i in order:
            for sign in (-1,1):
                candidate = values.copy()
                candidate[i] = np.clip(values[i]+sign*step,bounds[0][i],bounds[1][i])
                if candidate[i] == values[i]:
                    continue
                value = objective(candidate)
                if value < best-1e-9:
                    values,best = candidate,value
        trajectory.append(best)
    return model(values), dict(evaluations=calls,seconds=time.perf_counter()-start,initial_loss=old,
                               final_loss=best,trajectory=trajectory,values=values.tolist())


def parse():
    p = argparse.ArgumentParser()
    p.add_argument('--references',type=Path,required=True)
    p.add_argument('--rgb',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--raster',type=Path,required=True)
    p.add_argument('--cases',nargs='*')
    return p.parse_args()


def main():
    a = parse()
    engine = Engine()
    raster = Raster(a.raster)
    detector = _NativePoseLandmarker(a.model,segmentation=True)
    selected = json.loads((a.references/'configurations.json').read_text())
    names = list(dict.fromkeys(selected['globals']+selected['selected']))
    asymmetric = [key for key in engine.mods if key.startswith('armslegs/l-upperarm-scale-horiz-') and engine.defs[key]]
    names.extend(k for k in asymmetric if k not in names)
    fitted_defaults = np.array([engine.default[k] for k in names])
    bounds = np.array([[max(-.64,engine.mods[k][0].getMin()) if k not in selected['globals'] else
                        (.5 if k==engine.mac['Age'] else .04) for k in names],
                       [.96 if k in selected['globals'] else .64 for k in names]])
    native = lambda x:engine.extended(dict(zip(names,x)))*10
    current_names = [*morph_controls(engine.body),*length_controls(engine.body),*regional_controls(engine.body)]
    current = lambda x:engine.current(dict(zip(current_names,x)))*10
    current_bounds = np.repeat([[-.5],[.5]],len(current_names),axis=1)
    out = a.output
    (out/'measurements').mkdir(parents=True,exist_ok=True)
    (out/'meshes').mkdir(parents=True,exist_ok=True)
    dump(out/'measurements'/'config.json',dict(size=SIZE,seed=782,angles=ANGLES,g1_fields=names,
         g1_bounds=bounds.tolist(),g1_initial=fitted_defaults.tolist(),m6_fields=current_names,
         m6_bounds=current_bounds.tolist(),platform=platform.platform(),
         versions={k:version(k) for k in ('numpy','scipy','pillow','mediapipe','opencv-contrib-python')}))
    for file in sorted(a.references.glob('[AB]_*.npz')):
        case = file.stem
        if a.cases and case not in a.cases:
            continue
        print('CASE',case,flush=True)
        arrays, extraction, views = calibration(case,file,a.rgb/case,out/'maps'/case,detector,engine,raster)
        dump(out/'measurements'/f'{case}-extraction.json',extraction)
        results, meshes = {},{}
        triangles = arrays['faces']
        labels = triangle_regions(engine,triangles)
        all_views = [views[str(angle)] for angle in ANGLES]
        m6_views = [view for view in all_views if view['mask']['m6'].any()]
        rgb_views = all_views
        matched = m6_views if m6_views else all_views
        configs = [
            ('E0','m6','iou',m6_views,current,current_bounds,np.zeros(len(current_names))),
            ('E1','m6','iou',m6_views,native,bounds,fitted_defaults),
            ('E2','rgb','signed',matched,native,bounds,fitted_defaults),
            ('E3','rgb','chamfer',matched,native,bounds,fitted_defaults),
            ('E4','rgb','dense',matched,native,bounds,fitted_defaults),
            ('E4_full','rgb','dense',rgb_views,native,bounds,fitted_defaults),
            ('E9','truth','dense',matched,native,bounds,fitted_defaults),
            ('rgb_iou','rgb','iou',matched,native,bounds,fitted_defaults),
            ('rgb_gap','rgb','gap',matched,native,bounds,fitted_defaults),
            ('rgb_sparse','rgb','sparse',matched,native,bounds,fitted_defaults),
            ('rgb_sdf','rgb','sdf',matched,native,bounds,fitted_defaults),
        ]
        if case.startswith('A_'):
            configs.append(('region_oracle','truth','region',matched,native,bounds,fitted_defaults))
        if case in ('A_high_mass','A_heldout_1','B_female'):
            configs.extend((label,'rgb','dense',data,native,bounds,fitted_defaults) for label,data in
                           [('front',all_views[:1]),('side',all_views[1:2]),('oblique',all_views[3:4]),
                            ('front_side',all_views[:2]),('front_side_rear',all_views[:3])])
        alt_defaults = fitted_defaults.copy()
        alt_defaults[0] = .76
        for name, source, mode, subset, model, limits, default in configs:
            if not subset:
                results[name] = {'status':'no_valid_predicted_masks'}
                continue
            obs = [compile_view(view,source) for view in subset]
            v,row = coordinate_fit(model,limits,default,triangles,obs,mode,raster,region=labels)
            results[name] = row | {'views':[view['key'] for view in subset],'source':source,'objective':mode}
            meshes[name] = v
            print(case,name,round(row['seconds'],2),round(row['final_loss'],5),flush=True)
        if case in ('A_high_mass','A_heldout_1','B_female'):
            cam_bad = [compile_view(v,'rgb',camera=replace(v['camera'],yaw=v['camera'].yaw+9,span=223,roll=4.)) for v in all_views]
            bad_mask = views['occluded']
            mixed = [bad_mask,*all_views[1:]]
            for name,obs,init,robust,order in (
                ('camera_perturbation',cam_bad,fitted_defaults,False,None),
                ('alternate_seed',[compile_view(v,'rgb') for v in all_views],alt_defaults,False,None),
                ('reverse_order',[compile_view(v,'rgb') for v in all_views],fitted_defaults,False,list(reversed(range(len(names))))),
                ('occlusion_unmasked',[compile_view(v,'rgb') for v in mixed],fitted_defaults,False,None),
                ('occlusion_oracle_state',[compile_view(v,'rgb',occlusion=True) for v in mixed],fitted_defaults,False,None),
                ('duplicate_uniform',[compile_view(v,'rgb') for v in mixed+[bad_mask]*3],fitted_defaults,False,None),
                ('duplicate_robust',[compile_view(v,'rgb',occlusion=True,weight=.25 if v is bad_mask else 1.) for v in mixed+[bad_mask]*3],fitted_defaults,True,None),
                ('duplicate_only',[compile_view(v,'rgb',weight=.25 if v is bad_mask else 1.) for v in mixed+[bad_mask]*3],fitted_defaults,False,None),
                ('robust_only',[compile_view(v,'rgb') for v in mixed+[bad_mask]*3],fitted_defaults,True,None),
            ):
                meshes[name],results[name] = coordinate_fit(native,bounds,init,triangles,obs,'dense',raster,robust=robust,order=order)
        if 'M4' in arrays:
            meshes['E10'] = arrays['M4']
            results['E10'] = {'status':'replayed G1 M4 direct-geometry oracle'}
        ref = arrays['reference']
        rt = arrays['reference_faces']
        height = ref[np.unique(rt),1]
        levels = np.linspace(height.min()+.13*np.ptp(height),height.max()-.14*np.ptp(height),16)
        original = measurements(ref,rt,levels)
        for name,v in meshes.items():
            if not np.isfinite(v).all() or triangles.max()>=len(v) or triangles.min()<0:
                raise RuntimeError(f'Invalid experimental mesh {case} {name}')
            row = results[name]
            try:
                validate_rebind(engine.body,v/10)
                row['rebind'] = 'PASS'
            except ValueError as exc:
                row['rebind'] = str(exc)
            held = Camera(135)
            row['held_out'] = mask_metrics(raster.draw(held,v,triangles,384),raster.draw(held,ref,rt,384))
            delta = abs(measurements(v,triangles,levels)-original)
            row['section_mean_abs_mm'] = (10*delta.mean(0)).tolist()
            if case.startswith('A_'):
                row['matched_vertex_mm'] = summary(np.linalg.norm(v[engine.skin]-ref[engine.skin],axis=1)*10)
        np.savez_compressed(out/'meshes'/(case+'.npz'),faces=triangles,reference=ref,reference_faces=rt,**meshes)
        for key in ('E0','E1','E4','E9'):
            if key not in meshes:
                continue
            image = views['0']['rgb'].copy()
            projection = raster.draw(Camera(0),meshes[key],triangles,384)
            image[edge(projection)] = [39,221,180]
            save_png(out/'maps'/case/'0'/f'projection_{key}.png',image)
        dump(out/'measurements'/f'{case}-fits.json',results)
    detector.close()
    dump(out/'measurements'/'runtime.json',{'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})


if __name__ == '__main__':
    cv2.setNumThreads(1)
    main()
