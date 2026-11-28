"""Compose a labeled contact sheet from actual Blender renders."""
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont


def font(n,bold=False):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',n)
    except OSError:
        return ImageFont.load_default(size=n)


def main(images,score_path,dest):
    payload=json.loads(score_path.read_text())
    case,rows=next(iter(payload.items()))
    columns=[('reference','Riferimento'),('G2_E1','G2 · maschere M6'),('G4_M6','G4 · maschere M6'),
             ('G4_G3_SECTOR','G4 · camere G3 stimate')]
    views=[('0','Frontale'),('90','Profilo'),('180','Retro'),('45','Tre quarti'),('detail','Torso')]
    w,h=265,185
    cover=Image.new('RGB',(4*w+105,5*h+144),'#f4f7f6')
    draw=ImageDraw.Draw(cover)
    draw.text((23,18),'Human3D 2.0 / G4 · Geometria canonica',font=font(30,True),fill='#213e45')
    draw.text((24,59),case.replace('_',' ')+'  ·  Distanza media simmetrica dalla superficie di riferimento',
              font=font(15),fill='#536567')
    for col,(key,label) in enumerate(columns):
        x=96+col*w
        draw.text((x,89),label,font=font(15,True),fill='#213e45')
        if key in rows:
            d=rows[key]['symmetric_mm']['mean']
            draw.text((x,111),f'{d:.2f} mm',font=font(14),fill='#536567')
        for idx,(angle,title) in enumerate(views):
            y=134+idx*h
            if col==0:
                draw.text((10,y+79),title,font=font(13,True),fill='#34575c')
            image=Image.open(images/(f'{key}-{angle}.png')).convert('RGBA')
            image.thumbnail((w-8,h-6))
            tile=Image.new('RGBA',(w-9,h-7),'#e5ecec')
            tile.alpha_composite(image,((tile.width-image.width)//2,(tile.height-image.height)//2))
            cover.paste(tile.convert('RGB'),(x,y))
    cover.save(dest,optimize=True)


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
