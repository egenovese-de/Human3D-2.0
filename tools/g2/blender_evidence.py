# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender Workbench RGB fixtures and comparative assets. Run with Blender Python."""
import argparse
from pathlib import Path
import sys
import bpy
from mathutils import Vector, Matrix
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from projection import Camera

ANGLES = [0, 90, 180, 45]
DISPLAY = {"reference": (0.49, .52, .55), "E0": (.46, .55, .68),
           "E1": (.38, .53, .63), "E4": (.39, .63, .57),
           "E9": (.63, .52, .39), "E10": (.56, .53, .65)}


def basis(v):
    return np.column_stack([v[:,0],-v[:,2],v[:,1]]) / 100.


def mesh(name, vertices, triangles, color):
    data = bpy.data.meshes.new(name)
    data.from_pydata(basis(vertices).tolist(), [], triangles.tolist())
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.color = (*color, 1)
    for polygon in data.polygons:
        polygon.use_smooth = True
    return obj


def configure(size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    shade = scene.display.shading
    shade.light = 'STUDIO'
    shade.color_type = 'OBJECT'
    shade.show_shadows = False
    shade.show_cavity = False
    shade.show_specular_highlight = True
    scene.display.render_aa = '8'
    camera_data = bpy.data.cameras.new('Calibrated camera')
    camera = bpy.data.objects.new('Calibrated camera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera


def render(scene, obj, camera, target):
    right, up, toward = basis(camera.axes())*100
    origin = basis(np.array([[0, camera.center_y, 0]]))[0]
    obj.location = origin + toward*camera.distance/100
    obj.rotation_euler = Matrix(np.column_stack([right,up,toward]).tolist()).to_euler()
    obj.data.type = 'PERSP' if camera.perspective else 'ORTHO'
    obj.data.lens = 36 * camera.distance / camera.span
    obj.data.ortho_scale = camera.span/100
    obj.data.shift_x = -camera.dx
    obj.data.shift_y = camera.dy
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['fixtures','compare'])
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.output.mkdir(parents=True, exist_ok=True)
    with np.load(args.input) as arrays:
        ref = arrays['reference']
        triangles = arrays['reference_faces']
        center = 0.
        if args.mode == 'fixtures':
            scene, camera = configure(384)
            mesh('Reference', ref, triangles, (.53,.32,.22))
            for angle in ANGLES:
                render(scene, camera, Camera(angle, center_y=center), args.output/f'{angle}.png')
            if args.input.stem in ('A_high_mass','A_heldout_1'):
                render(scene,camera,Camera(35,center_y=center,elevation=12,distance=260,perspective=True),
                       args.output/'perspective.png')
            return
        scene, camera = configure(400)
        objects = {}
        for variant, color in DISPLAY.items():
            if variant not in arrays.files:
                continue
            objects[variant] = mesh(variant, arrays[variant], triangles if variant=='reference' else arrays['faces'], color)
        for variant, active in objects.items():
            for obj in objects.values():
                obj.hide_render = obj != active
            for angle in ANGLES:
                render(scene, camera, Camera(angle), args.output/f'{variant}-{angle}.png')
            if variant in ('reference','E0','E1','E4','E9','E10'):
                render(scene,camera,Camera(45,span=85,center_y=32),args.output/f'{variant}-detail.png')
        if args.input.stem.startswith('A_'):
            for i,obj in enumerate(objects.values()):
                obj.hide_render = False
                obj.location.x = i*2
            bpy.ops.wm.save_as_mainfile(filepath=str(args.output/'comparison.blend'))


if __name__ == '__main__':
    main()
