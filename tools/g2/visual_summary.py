"""Assemble Blender renders and measured overlays into labeled evidence plates."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def typeface(size, bold=False):
    path = '/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf'
    try:
        return ImageFont.truetype(path,size)
    except OSError:
        return ImageFont.load_default(size=size)


def composite(path,size,background='#e9eef1'):
    fg = Image.open(path).convert('RGBA')
    fg.thumbnail(size,Image.Resampling.LANCZOS)
    base = Image.new('RGBA',size,background)
    base.alpha_composite(fg,((size[0]-fg.width)//2,(size[1]-fg.height)//2))
    return base.convert('RGB')


def comparison(folder,target,scores,product,case):
    columns = [('reference','Reference'),('M6_product','M6 product'),('E1','G1 + M6 mask'),
               ('best','G2 contour + gap'),('E9','Photo oracle'),('E10','Geometry oracle')]
    variants = ['0','90','180','45','detail']
    row_titles = ['Front','Side','Rear','Three- quarter','Torso detail']
    w,h = 241,195
    plate = Image.new('RGB',(6*w+90,180+5*h),'#f5f6f4')
    draw = ImageDraw.Draw(plate)
    draw.text((35,24),'Human3D 2.0   /   G2 comparative geometry',fill='#173c44',font=typeface(31,True))
    draw.text((36,71),f'{case.replace("_"," ")}   •   Reference scale and camera held fixed in the calibrated fits',
              fill='#4c6265',font=typeface(17))
    for col,(key,title) in enumerate(columns):
        alias = key
        if key=='M6_product' and not (folder/'M6_product-0.png').exists():
            alias,title='E0','M6 calibrated probe'
        x = 86+col*w
        draw.text((x,118),title,fill='#173c44',font=typeface(16,True))
        source_key = 'rgb_gap' if key=='best' else alias
        score = product if alias=='M6_product' else scores.get(source_key)
        note = 'Mean symmetric distance' if key=='reference' else (('<0.001 mm' if score<.001 else f'{score:.3f} mm') if score is not None else 'Unavailable')
        draw.text((x,145),note,fill='#4c6265',font=typeface(14))
        for i,(tag,label) in enumerate(zip(variants,row_titles)):
            y = 173+i*h
            if col==0:
                for j,token in enumerate(label.split()):
                    draw.text((12,y+68+j*17),token,fill='#395358',font=typeface(12,True))
            path = folder/(alias+'-'+tag+'.png')
            if path.exists():
                plate.paste(composite(path,(w-9,h-8)),(x,y))
    plate.save(target,optimize=True)


def evidence_atlas(folder,target):
    raw = dict(np.load(folder/'estimated.npz'))
    gt = dict(np.load(folder/'oracle.npz'))
    signed = raw['signed_distance_px']
    z = np.clip(signed/16,-1,1)
    rgb = np.stack([152+80*z,190-25*abs(z),170-90*z],axis=2).astype(np.uint8)
    Image.fromarray(rgb).save(folder/'signed_distance.png')
    yy = np.arange(384)
    truth = gt['visible'].sum(axis=1)
    profile = raw['profiles_px'][:,2]
    fig,ax = plt.subplots(figsize=(3.84,3.84),dpi=100)
    ax.plot(truth,yy,label='Reference',color='#526ea6')
    ax.plot(profile,yy,label='RGB estimate',color='#289d80')
    ax.invert_yaxis()
    ax.set(xlabel='Foreground width (px)',ylabel='Image row (px)')
    ax.legend(loc='lower right',fontsize=8)
    fig.tight_layout()
    fig.savefig(folder/'profiles.png')
    plt.close(fig)
    panels = [('rgb.png','Blender RGB'),('M6_mask.png','M6 binary mask'),('negative_space.png','Observed gaps'),
              ('evidence_states.png','Evidence states'),('landmarks.png','MediaPipe landmarks'),
              ('landmark_regions.png','Landmark regions'),('oracle_regions.png','Rig-derived regions'),
              ('signed_distance.png','Signed distance'),('profiles.png','Dense width profile'),
              ('predicted_depth.png','Predicted relative depth'),('oracle_depth.png','Reference depth'),
              ('mask_error.png','RGB mask residual'),('projection_E0.png','M6 calibrated overlay'),
              ('projection_E1.png','G1 + M6 mask overlay'),('projection_E4.png','Dense profile overlay')]
    size = 260
    plate=Image.new('RGB',(5*(size+12)+30,3*(size+44)+90),'#f5f6f4')
    draw=ImageDraw.Draw(plate)
    draw.text((25,20),'G2 photographic evidence   /   frontal control',font=typeface(29,True),fill='#173c44')
    draw.text((26,61),'RGB-derived and calibrated reference channels shown side by side',font=typeface(15),fill='#526669')
    for i,(name,title) in enumerate(panels):
        x,y=18+(i%5)*(size+12),99+(i//5)*(size+44)
        file=folder/name
        if file.exists():
            plate.paste(composite(file,(size,size)),(x,y))
        draw.text((x,y+size+6),title,font=typeface(14,True),fill='#173c44')
    plate.save(target,optimize=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('experiment',type=Path)
    p.add_argument('renders',type=Path)
    p.add_argument('target',type=Path)
    p.add_argument('case')
    args=p.parse_args()
    exp,case=args.experiment,args.case
    scores={k:v['symmetric_mm']['mean'] for k,v in json.loads((exp/'scores'/(case+'.json')).read_text())[case].items()}
    product_file=exp/'product'/'surface.json'
    product=None
    if product_file.exists():
        product=json.loads(product_file.read_text()).get(case,{}).get('M6_product',{}).get('symmetric_mm',{}).get('mean')
    args.target.mkdir(parents=True,exist_ok=True)
    comparison(args.renders,args.target/'G2_Blender_Comparison.png',scores,product,case)
    evidence_atlas(exp/'maps'/case/'0',args.target/'G2_Evidence_Atlas.png')
    controls=json.loads((exp/'controls'/case/'controls.json').read_text())['contour_landscape']
    fig, axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
    for ax,kind,title in zip(axes,['shift','yaw','native_torso_width_neutral'],
                             ['Translation ±4% frame','Yaw ±18°','Native torso width around neutral']):
        for mode in ('iou','signed','chamfer','gap','dense','sdf'):
            values=np.asarray(controls[mode][kind])
            scaled=(values-values.min())/max(1e-9,np.ptp(values))
            ax.plot(np.linspace(-1,1,25),scaled,label=mode)
        ax.set(title=title,xlabel='Normalized perturbation',ylabel='Normalized loss')
    axes[-1].legend(loc='best',fontsize=8)
    fig.savefig(args.target/'G2_Contour_Landscapes.png',dpi=165)
    plt.close(fig)


if __name__=='__main__':
    main()
