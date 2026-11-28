"""Compose published atlases from Blender renders and measured section loops."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from visualize import atlas


def open_image(file):
    return Image.open(file).copy() if file.exists() else None


def main(root, delivery):
    delivery.mkdir(parents=True,exist_ok=True)
    geometry=root/'render'/'geometry'
    photo=root/'render'/'photo'
    proposals=root/'render'/'proposed'
    truth=json.loads((root/'study/A_slim/surface.json').read_text())
    photo_truth=json.loads((root/'photo/A_heldout_1/surface.json').read_text())
    names={'reference':'Reference','D0':'D0 M7','R1_extended':'R1 native','R2_fine':'R2 fine FFD',
           'R3_cage':'R3 cage','R4_graph120':'R4 graph','R5_symmetric':'R5 registration',
           'R6_graph':'R6 hybrid','initial':'Native initial','R0_long':'R0 extended budget',
           'B_estimated':'M7 estimated','P_oracle_4_ffd':'Exact mask FFD',
           'P_calibrated_rgb_ffd':'Calibrated RGB FFD','P_estimated_rgb_ffd':'Estimated RGB FFD',
           'P_stress_yaw_ffd':'Yaw +8° FFD'}
    def render_images(folder, keys, views):
        return [[open_image(folder/f'{key}-{view}.png') for view in views] for key in keys]
    def report(name, title, subtitle, folder, keys, views, headers, numbers, score='accepted'):
        labels=[names[k]+(f"\n{numbers[k][score]['mean']:.2f} mm" if k in numbers else '') for k in keys]
        atlas(title,subtitle,headers,labels,render_images(folder,keys,views),delivery/name)
    keys=('reference','D0','R1_extended','R2_fine','R3_cage','R4_graph120','R5_symmetric','R6_graph')
    report('G6_Blender_Comparison.png','G6 canonical reconstruction','A_slim · retained meshes · symmetric surface distance',
           geometry,keys,(0,90,180,45),['Front','Profile','Rear','Oblique'],truth)
    report('G6_Regional_Error_Atlas.png','G6 error and displacement','A_slim · reference distance 0–25 mm · motion from M7 0–55 mm',
           geometry,keys[1:],(45,'error','displacement'),['Blender geometry','Reference distance','Vertex displacement'],truth)
    stage=json.loads((root/'study/A_adult_asymmetric/surface.json').read_text())
    report('G6_Deformation_Stages.png','G6 proposed deformation stages',
           'A_adult_asymmetric · candidate geometry before the independent crossing screen',
           proposals,('reference','D0','initial','R0_long','R1_extended','R2_fine','R4_graph120','R6_graph'),
           (45,),['Blender oblique'],stage,score='proposal')
    report('G6_Photographic_Transfer_Comparison.png','G6 photographic transfer',
           'A_heldout_1 · retained outputs · calibrated and estimated tests use separate M7 anchors',
           photo,('reference','D0','B_estimated','P_oracle_4_ffd','P_calibrated_rgb_ffd',
                  'P_estimated_rgb_ffd','P_stress_yaw_ffd'),(45,),['Blender oblique'],photo_truth)
    sections=json.loads((root/'section_plot_data.json').read_text())
    fig, axes=plt.subplots(1,3,figsize=(11,4.5),constrained_layout=True)
    for p,key in zip(axes,('abdomen','waist','hip')):
        for name,c in [('reference','#202b35'),('D0','#b75e48'),('R2_fine','#127589')]:
            if name not in sections.get(key,{}):
                continue
            loop=np.asarray(sections[key][name])
            loop=np.r_[loop,loop[:1]]
            p.plot(loop[:,0],loop[:,1],label=names[name],color=c,lw=1.6)
        p.set(title=key.title(),xlabel='Lateral (cm)',ylabel='Anterior–posterior (cm)',aspect='equal')
        p.grid(alpha=.17)
    axes[0].legend(frameon=False)
    fig.suptitle('G6 fixed anatomical sections · A_slim',fontweight='bold')
    fig.savefig(delivery/'G6_Anatomical_Sections.png',dpi=160)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('root',type=Path)
    p.add_argument('delivery',type=Path)
    a=p.parse_args()
    main(a.root,a.delivery)
