"""Blender comparison, wireframe, and vertex error for publishable Family A."""
import argparse
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

parser=argparse.ArgumentParser(description=__doc__)
for key in ('g4','source','output'):
    parser.add_argument(key,type=Path)
parser.add_argument('--keys',nargs='+',required=True)
parser.add_argument('--all-views',action='store_true')
parser.add_argument('--archive-scene',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sys.path.insert(0,str(args.g4.resolve()/'tools/g2'))
from blender_evidence import Camera, configure, mesh, render

scene,cam=configure(384)
args.output.mkdir(parents=True,exist_ok=True)
with np.load(args.source) as data:
    ref=data['reference'] if 'reference' in data.files else None
    rf=data['reference_faces'] if ref is not None else None
    faces=data['faces']
    objects=[]
    for key in args.keys:
        if key not in data.files:
            continue
        case_faces=rf if key=='reference' else faces
        v=data[key]
        obj=mesh(key,v,case_faces,(.53,.61,.67) if key!='reference' else (.62,.57,.53))
        objects.append(obj)
        for yaw in ((0,90,180,45) if args.all_views else (45,)):
            render(scene,cam,Camera(yaw,span=215,distance=420,perspective=True),args.output/f'{key}-{yaw}.png')
        if key != 'reference' and ref is not None and args.all_views:
            b=BVHTree.FromPolygons(ref.tolist(),rf.tolist(),all_triangles=True)
            error=np.fromiter((b.find_nearest(q)[3]*10 for q in v),float,count=len(v))
            shade=np.minimum(error/25,1)
            colors=np.stack([.10+.9*shade,.65-.5*shade,.74-.59*shade,np.ones(len(v))],axis=1)
            attr=obj.data.color_attributes.new(name='Reference error mm',type='FLOAT_COLOR',domain='POINT')
            attr.data.foreach_set('color',colors.astype(np.float32).ravel())
            obj.data.color_attributes.active_color=attr
            scene.display.shading.color_type='VERTEX'
            render(scene,cam,Camera(45,span=215,distance=420,perspective=True),args.output/f'{key}-error.png')
            scene.display.shading.color_type='OBJECT'
            if 'D0' in data.files:
                move=np.minimum(np.linalg.norm(v-data['D0'],axis=1)*10/55,1)
                colors=np.stack([.12+.83*move,.32+.44*move,.66-.54*move,np.ones(len(v))],axis=1)
                dv=obj.data.color_attributes.new(name='Displacement relative to M7',type='FLOAT_COLOR',domain='POINT')
                dv.data.foreach_set('color',colors.astype(np.float32).ravel())
                obj.data.color_attributes.active_color=dv
                scene.display.shading.color_type='VERTEX'
                render(scene,cam,Camera(45,span=215,distance=420,perspective=True),args.output/f'{key}-displacement.png')
                scene.display.shading.color_type='OBJECT'
        if key in ('R2_fine','R6_graph') and args.all_views:
            mod=obj.modifiers.new('Wireframe preview','WIREFRAME')
            mod.thickness=.0014
            render(scene,cam,Camera(45,span=215,distance=420,perspective=True),args.output/f'{key}-wire.png')
            obj.modifiers.remove(mod)
        obj.hide_render=True
    if args.archive_scene:
        for idx,obj in enumerate(objects):
            obj.hide_render=False
            obj.location.x=idx*2
        bpy.ops.wm.save_as_mainfile(filepath=str((args.output/'G6_editable_comparison.blend').resolve()))
