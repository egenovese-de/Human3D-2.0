# SPDX-License-Identifier: GPL-3.0-or-later
"""Render canonical G2/G4 comparisons for same-topology fixtures."""
from pathlib import Path
import sys
import numpy as np
import bpy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'g2'))
from blender_evidence import configure, mesh, render
from projection import Camera

PANELS=[
    ('reference','Reference',(.47,.53,.56)),
    ('G2_E1','G2 with M6 masks',(.4,.53,.65)),
    ('G4_M6','G4 with M6 masks',(.34,.62,.54)),
    ('G4_G3_SECTOR','G4 with estimated G3 cameras',(.63,.44,.38)),
]
ANGLES=(0,90,180,45)


def uv_loops(obj_file, faces):
    uv=[]
    indices=[]
    group=''
    with obj_file.open() as handle:
        for line in handle:
            data=line.split()
            if not data:
                continue
            if data[0]=='g':
                group=' '.join(data[1:])
            elif data[0]=='vt':
                uv.append(list(map(float,data[1:3])))
            elif data[0]=='f' and group=='body':
                vertices=[tuple(int(v)-1 for v in x.split('/')[:2]) for x in data[1:]]
                indices.extend([vertices[0],vertices[i],vertices[i+1]] for i in range(1,len(vertices)-1))
    indices=np.asarray(indices)
    if not np.array_equal(indices[:,:,0],faces):
        raise ValueError('pinned UV corner order differs from canonical mesh')
    return np.asarray(uv,dtype=np.float32)[indices[:,:,1].ravel()].ravel()


def main(data, obj, output):
    output.mkdir(exist_ok=True,parents=True)
    scene,camera=configure(320)
    inputs=np.load(data)
    faces=inputs['faces']
    if not np.array_equal(faces,inputs['reference_faces']):
        raise ValueError('This deliverable only admits redistributable MakeHuman topology')
    uv=uv_loops(obj,faces)
    objects={}
    for key,label,color in PANELS:
        o=mesh(label,inputs[key],faces,color)
        layer=o.data.uv_layers.new(name='MakeHuman UV')
        layer.data.foreach_set('uv',uv)
        objects[key]=o
    vertical=inputs['reference'][np.unique(faces),1]
    span=max(215.,1.16*np.ptp(vertical))
    center=float((vertical.max()+vertical.min())/2)
    for key,o in objects.items():
        for other in objects.values():
            other.hide_render=other!=o
        for angle in ANGLES:
            render(scene,camera,Camera(angle,span=span,center_y=center),output/(f'{key}-{angle}.png'))
        render(scene,camera,Camera(45,span=90,center_y=28),output/(f'{key}-detail.png'))
    for i,o in enumerate(objects.values()):
        o.hide_render=False
        o.location.x=2*i
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'G4_Canonical_Comparison.blend'))


if __name__=='__main__':
    main(*map(Path,sys.argv[sys.argv.index('--')+1:]))
