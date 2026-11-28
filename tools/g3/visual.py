"""Build a registration plate from rendered RGB and actual projected contours."""
from pathlib import Path
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_erosion


def font(size, bold=False):
    base='/usr/share/fonts/truetype/dejavu/DejaVuSans'
    try:
        return ImageFont.truetype(base+('-Bold' if bold else '')+'.ttf',size)
    except OSError:
        return ImageFont.load_default(size=size)


def main(source, target):
    rgb=Image.open(source/'rgb.png').convert('RGB')
    record=json.loads((source.parent/'registration.json').read_text())['views'][source.name]['fits']
    plate=Image.new('RGB',(1240,555),'#f5f7f6')
    draw=ImageDraw.Draw(plate)
    draw.text((24,18),'Human3D 2.0  /  Registrazione articolata G3',font=font(31,True),fill='#18373e')
    draw.text((25,60),'Prova prospettica Blender · posa di osservazione separata dalla forma canonica',
              font=font(16),fill='#516367')
    variants=[(None,'RGB di riferimento'),('oracle_anchors_perspective','Ancoraggi esatti · camera stimata'),
              ('rgb_nominal_shape','Ancoraggi RGB · anatomia nominale')]
    for index,(key,title) in enumerate(variants):
        x=23+index*406
        image=rgb.copy()
        caption='Immagine di acquisizione sintetica'
        if key:
            artifact=np.load(source/(key+'.npz'))
            pixels=np.asarray(image).copy()
            for field,color in [('reference',(46,217,185)),('predicted',(236,111,66))]:
                mask=artifact[field]
                edge=mask & ~binary_erosion(mask)
                layer=Image.fromarray(edge.astype('uint8')*255).resize(rgb.size,Image.Resampling.NEAREST)
                pixels[np.asarray(layer)>0]=color
            image=Image.fromarray(pixels)
            overlay=ImageDraw.Draw(image)
            for a,b in zip(artifact['reference_xy'],artifact['prediction_xy']):
                overlay.line([tuple(a),tuple(b)],fill='#f0d55b',width=2)
                overlay.ellipse((a[0]-2,a[1]-2,a[0]+2,a[1]+2),fill='#1d4d70')
            row=record[key]
            caption=f'{row["anchor_mean_px"]:.1f} px di errore medio   /   IoU {row["mask_iou"]:.3f}'
        plate.paste(image,(x,112))
        draw.text((x,86),title,font=font(15,True),fill='#18373e')
        draw.text((x,504),caption,font=font(14),fill='#516367')
    draw.text((24,532),'Verde: contorno di riferimento   ·   Arancio: contorno stimato   ·   Giallo: residuo degli ancoraggi',
              font=font(12),fill='#365457')
    plate.save(target,optimize=True)


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
