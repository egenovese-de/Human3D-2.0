"""Build local RGB-only and oracle evidence for authorized MB-Lab hold-outs."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

from evidence import rgb_uniform
from g1_benchmark import dump
from human3d.vision import _NativePoseLandmarker
from photographic import rgb_image
from projection import Camera, Raster


def main(refs, inputs, model, raster_path):
    cv2.setNumThreads(1)
    raster=Raster(raster_path)
    detector=_NativePoseLandmarker(model,segmentation=True)
    for path in sorted(refs.glob('B_*.npz')):
        mesh=np.load(path)
        for angle in ('0','90','180','45'):
            directory=inputs/'evidence_maps'/path.stem/angle
            directory.mkdir(parents=True,exist_ok=True)
            rgba=np.asarray(Image.open(inputs/'rgb'/path.stem/(angle+'.png')).convert('RGBA'))
            rgb,_=rgb_image(rgba,'plain')
            rgb_path=directory/'rgb.png'
            Image.fromarray(rgb).save(rgb_path)
            detected=detector.detect(rgb_path,sha256(rgb_path.read_bytes()).hexdigest())
            m6=np.zeros(rgb.shape[:2],bool)
            if len(detected.candidates)==1 and detected.masks and detected.masks[0]:
                m6=np.asarray(Image.open(BytesIO(detected.masks[0])))>0
            cam=Camera(int(angle))
            exact=raster.draw(cam,mesh['reference'],mesh['reference_faces'],384)
            np.savez_compressed(directory/'estimated.npz',mask_rgb=rgb_uniform(rgb),mask_m6=m6)
            np.savez_compressed(directory/'oracle.npz',body=exact)
            dump(directory/'camera.json',cam.manifest(384))
        print(path.stem,flush=True)
    detector.close()


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
