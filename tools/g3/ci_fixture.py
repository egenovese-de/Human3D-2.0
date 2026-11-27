"""Convert a pinned Blender fixture into the G3 benchmark wire format."""
import json
from pathlib import Path
import shutil
import sys
from PIL import Image
import numpy as np
from photographic import rgb_image
from projection import Camera


def main(reference,rgba,output):
    geo=output/'geometry'
    observations=output/'evidence_maps'/reference.stem/'0'
    geo.mkdir(parents=True,exist_ok=True)
    observations.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(reference,geo/reference.name)
    rgb,_=rgb_image(np.asarray(Image.open(rgba).convert('RGBA')),'plain')
    Image.fromarray(rgb).save(observations/'rgb.png')
    (observations/'camera.json').write_text(json.dumps(Camera(0).manifest(384))+'\n')


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
