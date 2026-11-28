"""Render the G5 appearance controls with Blender Workbench."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

g4, source, destination = map(Path, sys.argv[sys.argv.index('--') + 1:])
sys.path.insert(0, str(g4.resolve() / 'tools/g2'))
from blender_evidence import Camera, configure, mesh, render

config = json.loads(Path(__file__).with_name('config.json').read_text())
for file in sorted(source.glob('*.npz')):
    scene, camera = configure(config['image_size'])
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new('Studio')
    scene.world.color = (.32, .37, .41)
    scene.display.shading.color_type = 'MATERIAL'
    with np.load(file) as asset:
        points, faces, altered = (asset[k] for k in ('reference', 'reference_faces', 'modified'))
        body = mesh('Visible subject', points, faces, (.53, .32, .22))
        palette = [(.53,.32,.22), (.12,.36,.44), (.09,.20,.30)]
        for i, color in enumerate(palette):
            mat = bpy.data.materials.new(f'Studio material {i}')
            mat.diffuse_color = (*color, 1)
            body.data.materials.append(mat)
        for index in np.flatnonzero(altered):
            center = points[faces[index]].mean(axis=0)
            material = 1 + int(np.sin(center[1] * .5 + center[0] * .16) > .65)
            body.data.polygons[int(index)].material_index = material
            if file.stem == 'external_panel':
                body.data.polygons[int(index)].use_smooth = False
        if file.stem == 'striped_background':
            # Wide vertical props behind the body add visible texture.
            for k in range(-3, 4):
                bpy.ops.mesh.primitive_cube_add(size=1, location=(k*.46, 1.2, 0.))
                bar = bpy.context.object
                bar.scale = (.22, .03, 3.)
                bar.data.materials.append(body.data.materials[1 if k % 2 else 2])
        destination_case = destination / file.stem
        destination_case.mkdir(parents=True, exist_ok=True)
        for yaw in (0, 90):
            render(scene, camera, Camera(yaw, **config['main_camera_cm']),
                   destination_case / f'{yaw}.png')
