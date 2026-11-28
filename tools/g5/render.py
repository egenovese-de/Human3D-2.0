"""Blender RGB fixtures using the pinned G2 calibrated renderer."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

args = sys.argv[sys.argv.index('--') + 1:]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('g4', type=Path)
parser.add_argument('refs', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--case')
parser.add_argument('--compare', action='store_true')
options = parser.parse_args(args)
sys.path.insert(0, str(options.g4.resolve() / 'tools/g2'))
from blender_evidence import Camera, configure, mesh, render

config = json.loads(Path(__file__).with_name('config.json').read_text())
if options.compare:
    source = options.refs
    scene, camera = configure(320)
    colors = [(0.50,.55,.59), (.50,.55,.59)]
    options.output.mkdir(parents=True, exist_ok=True)
    with np.load(source) as data:
        for i, key in enumerate(k for k in data.files if k not in ('faces', 'reference_faces', 'error_mm', 'displacement_mm')):
            obj = mesh(key, data[key], data['reference_faces' if key == 'reference' else 'faces'], colors[i % 2])
            for yaw in (0, 90, 180, 45):
                render(scene, camera, Camera(yaw, **config['main_camera_cm']), options.output / f'{key}-{yaw}.png')
            render(scene, camera, Camera(45, span=82, center_y=18, distance=420, perspective=True),
                   options.output / f'{key}-detail.png')
            for channel in ('error_mm', 'displacement_mm'):
                if key != 'D7' or channel not in data:
                    continue
                values = np.clip(data[channel] / (5 if channel == 'displacement_mm' else 25), 0, 1)
                rgba = np.c_[.15+.80*values, .72-.52*values, .72-.60*values, np.ones_like(values)]
                attr = obj.data.color_attributes.new(name=channel, type='FLOAT_COLOR', domain='POINT')
                attr.data.foreach_set('color', rgba.astype(np.float32).ravel())
                obj.data.color_attributes.active_color = attr
                scene.display.shading.color_type = 'VERTEX'
                render(scene, camera, Camera(45, **config['main_camera_cm']), options.output / f'{key}-{channel}.png')
                scene.display.shading.color_type = 'OBJECT'
            obj.hide_render = True
else:
    for source in sorted(options.refs.glob('*.npz')):
        if options.case and options.case != source.stem:
            continue
        scene, camera = configure(config['image_size'])
        with np.load(source) as data:
            obj = mesh('Reference', data['reference'], data['reference_faces'], (.53, .32, .22))
            folder = options.output / source.stem
            folder.mkdir(parents=True, exist_ok=True)
            for yaw in config['fit_yaw_deg'] + config['holdout_yaw_deg']:
                render(scene, camera, Camera(yaw, **config['main_camera_cm']), folder / f'{yaw}.png')
            obj.color = (.31, .48, .57, 1)
            scene.display.shading.studiolight_rotate_z = 1.3
            for yaw in (0, 90):
                render(scene, camera, Camera(yaw, **config['main_camera_cm']), folder / f'{yaw}-alternate.png')
