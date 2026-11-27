"""Repeat controlled articulated and occluded views with actual Blender RGB."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
import cv2
from PIL import Image
from g1_benchmark import Engine, dump
from human3d.vision import _NativePoseLandmarker
from photographic import rgb_image
from projection import Raster
from registration import FIT_SIZE, Rig
from benchmark import evaluate, g2_camera


def main():
    p=argparse.ArgumentParser()
    p.add_argument('root',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('model',type=Path)
    p.add_argument('library',type=Path)
    p.add_argument('--blender',default='blender')
    a=p.parse_args()
    cv2.setNumThreads(1)
    engine=Engine()
    raster=Raster(a.library)
    detector=_NativePoseLandmarker(a.model,segmentation=True)
    nominal=Rig(engine.body['rig'],engine.extended({})*10)
    for subject in ('A_high_mass','A_heldout_1'):
        for mode in ('near_articulated','far_articulated','cropped_occluded'):
            source=next(iter(sorted(a.root.glob('A_*/'+subject+'/'+mode))),None)
            if source is None:
                continue
            out=a.output/subject/mode
            out.mkdir(parents=True,exist_ok=True)
            base=json.loads((source.parent/'registration.json').read_text())
            cam=g2_camera(base['views'][mode]['truth_camera'])
            args=[a.blender,'-b','-t','2','--factory-startup','--python-exit-code','1','--python',
                  str(Path(__file__).with_name('blender_g3.py')),'--','fixtures',str(source),str(out)]
            with (out/'blender.log').open('w') as log:
                subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT)
            rgba=np.array(Image.open(out/'reference.png'))
            rgb,_=rgb_image(rgba,'plain')
            crop=mode=='cropped_occluded'
            if crop:
                rgb[276:]=[215,222,231]
                rgb[132:226,158:218]=[49,91,139]
            img=out/'rgb.png'
            Image.fromarray(rgb).save(img)
            truth=np.load(source/'truth.npz')
            ref=Rig(engine.body['rig'],truth['rest_cm'])
            config=FIT_SIZE*cam.distance/cam.span
            result=evaluate(False,img,out,ref,nominal,engine,cam,truth['pose_parameters'],truth['faces'],raster,detector,config,crop=crop)
            results={'views':{mode:result}}
            dump(out.parent/'registration.json',merge_views(out.parent/'registration.json',results))
            print(subject,mode,{k:round(v['anchor_mean_px'],2) for k,v in result['fits'].items() if v['status']=='ok'},flush=True)
    detector.close()


def merge_views(path,payload):
    if not path.is_file():
        return payload
    old=json.loads(path.read_text())
    return {'views':old['views']|payload['views']}

if __name__=='__main__':
    main()
