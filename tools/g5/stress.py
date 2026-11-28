"""Controlled observation-pose, garment-shell and external-occlusion tests."""
from dataclasses import replace
import json
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np

from evidence import CONFIG, SIZE, Evidence, visible_surface
from lab_search import bounded_fit
from observations import DenseLoss, observation_vertices
from projection import Camera, Raster
from human3d.experimental import NativeBasis, Observation, RegisteredPose
from human3d.experimental_registration import POSE_KEYS, Rig
from human3d.frozen_body import load_project_body
from human3d.session import Session


def motion(degrees):
    values = np.zeros(len(POSE_KEYS))
    values[:8] = np.deg2rad(np.array([-1., .6, -1.3, .9, .8, -.5, .5, -.5]) * degrees)
    return values


def shell(vertices, thickness):
    y = vertices[:, 1]
    width = np.abs(vertices[:, 0])
    band = np.clip((y - 2) / 8, 0, 1) * np.clip((57 - y) / 10, 0, 1)
    band *= np.clip((25 - width) / 8, 0, 1)
    points = vertices.copy()
    points[:, 2] += thickness * band * np.tanh(vertices[:, 2] / 6)
    points[:, 0] += thickness * .4 * band * np.tanh(vertices[:, 0] / 8)
    return points


def main(runtime, source, raster_path, baseline, out):
    out.mkdir(parents=True, exist_ok=True)
    session = Session(baseline / 'project')
    body = load_project_body(session.store)
    basis = NativeBasis(runtime, body)
    with np.load(source) as data:
        ref, faces, ref_faces = (data[name] for name in ('reference', 'faces', 'reference_faces'))
    raster = Raster(raster_path)
    rig = Rig(body['rig'], basis.evaluate({}) * 10)
    ref_rig = Rig(body['rig'], ref)
    settings = [
        ('mild_correct', [15, 15], [15, 15], 0, 'body'),
        ('mild_error', [15, 15], [8, 8], 0, 'body'),
        ('strong_mixed_correct', [38, -28], [38, -28], 0, 'body'),
        ('strong_mixed_error', [38, -28], [21, -16], 0, 'body'),
        ('close_shell_naive', [0, 0], [0, 0], 1.5, 'naive'),
        ('loose_shell_naive', [0, 0], [0, 0], 6, 'naive'),
        ('loose_shell_exclude', [0, 0], [0, 0], 6, 'exclude'),
        ('block_occlusion_exclude', [0, 0], [0, 0], 0, 'external'),
        ('block_occlusion_naive', [0, 0], [0, 0], 0, 'external-naive'),
    ]
    report = {}
    for tag, true_pose, assumed_pose, protrusion, treatment in settings:
        cameras, views, observations, variants = {}, [], {}, {}
        metadata = report[tag] = {'reference_pose_degrees': true_pose, 'assumed_pose_degrees': assumed_pose,
                                  'shell_thickness_cm': protrusion, 'treatment': treatment}
        for yaw, true, assumed in zip((0, 90), true_pose, assumed_pose):
            key = str(yaw)
            camera = cameras[key] = Camera(yaw, **CONFIG['main_camera_cm'])
            original = ref_rig.mesh(motion(true))
            dressed = shell(original, protrusion)
            surface = visible_surface(raster, camera, dressed, ref_faces, SIZE)
            domain, foreground = surface.valid.copy(), surface.mask.copy()
            if treatment == 'exclude':
                altered = (np.linalg.norm(dressed - original, axis=1) > .05)[ref_faces].any(axis=1)
                domain &= ~altered[np.maximum(surface.triangle, 0)]
            if treatment.startswith('external'):
                block = np.zeros_like(domain)
                block[129:211, 143:216] = True
                if treatment == 'external':
                    domain &= ~block
                else:
                    foreground &= ~block
                    domain &= foreground
                # The exclusion arm keeps the exact body silhouette as a diagnostic
                # oracle, isolating damage from the dense channel without detector bias.
            views.append(Observation(key, foreground,
                         lambda points, size, c=camera: c.project(points * 10, size)[:, :2],
                         RegisteredPose(rig, motion(assumed)) if assumed else None,
                         'controlled synthetic pose', 0, 'independent'))
            observations[key] = {
                 name: Evidence(key, 'controlled geometry', 'G5', convention, (SIZE, SIZE), (SIZE, SIZE),
                                'identity', foreground, surface.mask, domain, channel, 'calibrated',
                                'independent', 'ground truth')
                 for name, channel, convention in [('depth', surface.depth_cm, 'camera Z cm'),
                                                   ('normal', surface.normals, 'right up toward')]}
        for variant, loss in [('D0', None), ('D3', DenseLoss(raster, faces, cameras, observations,
                                                            ('depth', 'normal')))]:
            start = perf_counter()
            points, _, _, fit = bounded_fit(basis, body, views, lambda: None, loss)
            variants[variant] = points * 10
            metadata[variant] = fit | {'seconds': perf_counter() - start}
        np.savez_compressed(out / (tag + '.npz'), reference=ref, reference_faces=ref_faces, faces=faces, **variants)
        print(tag, metadata, flush=True)
    (out / 'fit.json').write_text(json.dumps(report, indent=2))

if __name__ == '__main__':
    cv2.setNumThreads(1)
    main(*map(Path, sys.argv[1:]))
