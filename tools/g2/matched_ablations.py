"""Common-mask isolations for post-processing, negative space, and landmarks."""
from pathlib import Path
import json
import sys
import cv2
import numpy as np
from g1_benchmark import Engine, dump
from evidence import edge
from photographic import ANGLES, SIZE, anchor_points, compile_view, coordinate_fit
from projection import Camera, Raster


def main(experiment,out,library):
    out.mkdir(exist_ok=True,parents=True)
    e = Engine()
    raster = Raster(library)
    config = json.loads((experiment/'measurements/config.json').read_text())
    names = config['g1_fields']
    initial = np.asarray(config['g1_initial'])
    bounds = np.asarray(config['g1_bounds'])
    native = lambda x:e.extended(dict(zip(names,x)))*10
    for case in ('A_adult_asymmetric','A_high_mass','A_heldout_1'):
        source = np.load(experiment/'meshes'/(case+'.npz'))
        faces = source['faces']
        meshes = {k:source[k] for k in ('reference','reference_faces','faces')}
        options = {}
        for angle in ANGLES:
            folder = experiment/'maps'/case/str(angle)
            gt,raw = dict(np.load(folder/'oracle.npz')),dict(np.load(folder/'estimated.npz'))
            if not raw['mask_m6'].any():
                continue
            view = dict(camera=Camera(angle),mask={'m6':raw['mask_m6'],'grabcut':raw['mask_refined'],
                                                   'rgb':raw['mask_rgb'],'oracle':gt['body']})
            landmarks = raw['landmarks_px']
            ids = gt['anchor_id']
            subset = (landmarks[ids,2]>=.8)&(landmarks[ids,3]>=.8)
            for key in view['mask']:
                obs = compile_view(view,key)
                obs['ids'] = ids[subset]
                obs['model_joint_observed'] = landmarks[ids[subset],:2]*SIZE/384
                obs['model_joint_oracle'] = gt['anchors_px'][subset]*SIZE/384
                options.setdefault(key,[]).append(obs)
        def penalty(kind):
            def extra(pred,depth,ids,obs,vertices):
                if kind=='gap':
                    return .45 * float(np.count_nonzero(pred&obs['gap'])/obs['size'])
                if not len(obs['ids']):
                    return 0.
                joints = anchor_points(e,vertices)
                xy = obs['camera'].project(np.stack([joints[i] for i in obs['ids']]),SIZE)[:,:2]
                d = np.linalg.norm(xy-obs['model_joint_'+kind],axis=1)
                return .10*float(np.minimum(d,12).mean())/7
            return extra
        results = {}
        for name,channel,term in [('current_mask','m6',None),('grabcut_mask','grabcut',None),
                                  ('rgb_mask','rgb',None),('oracle_mask','oracle',None),
                                  ('explicit_gap','m6','gap'),('predicted_landmarks','m6','observed'),
                                  ('projected_joint_oracle','m6','oracle')]:
            extra = penalty(term) if term else None
            meshes[name],results[name] = coordinate_fit(native,bounds,initial,faces,options[channel],'chamfer',
                                                        raster,extra=extra)
        dump(out/(case+'.json'),results)
        np.savez_compressed(out/(case+'.npz'),**meshes)
        print(case,flush=True)


if __name__=='__main__':
    cv2.setNumThreads(1)
    main(*map(Path,sys.argv[1:]))
