"""Adapter from admitted Engine B views to isolated geometric channels."""
from copy import copy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion

from evidence import (CONFIG, SIZE, Evidence, affine_inverse, aligned_depth, angles,
                      dsine_to_camera, huber, resized, unit, visible_surface)
from human3d.experimental import RegisteredPose, registrations
from projection import Camera
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.reconstruction import Diagnostics


@dataclass(frozen=True)
class EstimatedProjection:
    project_pixels: object
    frame: np.ndarray
    distance: float = 420.
    perspective: bool = False

    def axes(self):
        return self.frame

    def project(self, vertices, size):
        return np.c_[self.project_pixels(vertices / 10, size), self.distance - vertices @ self.frame[2]]


def admit(body, basis, session, angles_by_id, directory, estimated):
    nominal = basis.evaluate({})
    native_body = body | {'mesh': body['mesh'] | {'vertices': nominal},
                          'rig': body['rig'] | {'joints': rebind_joints(body['rig'], nominal)}}
    diagnostics = Diagnostics('G5', 'geometry')
    definitions = {}
    if not estimated:
        import json
        definitions = {v['photo_sha256']: v
                       for v in json.loads((directory / 'calibration.json').read_text())['views']}
    views, _ = registrations(native_body, session.shared_evidence(), definitions, diagnostics, lambda: None)
    cameras = {}
    for view in views:
        if not estimated:
            cameras[view.id] = Camera(angles_by_id[view.id], **CONFIG['main_camera_cm'])
        else:
            points = view.project(np.vstack((np.zeros(3), np.eye(3))), SIZE)
            right, down = unit((points[1:] - points[0]).T)
            # Align depth with the admitted yaw. The image similarity can
            # include a horizontal parity flip, so its determinant is insufficient.
            yaw = np.deg2rad(view.pose.camera.yaw_degrees)
            towards = np.array([-np.sin(yaw), 0., np.cos(yaw)])
            frame = np.stack((right, -down, towards))
            cameras[view.id] = EstimatedProjection(view.project, frame)
    return views, cameras, diagnostics.metrics


def observation_vertices(body, vertices, view):
    if view.pose is None:
        return vertices
    rig = body['rig']
    joints = rebind_joints(rig, vertices)
    transforms = (view.pose.transforms(joints) if isinstance(view.pose, RegisteredPose)
                  else pose_transforms(rig, joints, view.pose))
    return np.asarray(skin_vertices(vertices, rig['skin'], transforms))


class DenseLoss:
    def __init__(self, raster, faces, cameras, maps, mode, estimate=False):
        self.raster, self.faces, self.cameras, self.maps = raster, faces, cameras, maps
        self.mode, self.estimate = mode, estimate
        self.cache = {}

    def components(self, view, points, size):
        key = view.id, size
        if key not in self.cache:
            values = self.maps[view.id]
            self.cache[key] = {name: (resized(item.valid.astype(np.uint8), size).astype(bool),
                                      resized(item.values, size)) for name, item in values.items()}
        observed = self.cache[key]
        drawn = visible_surface(self.raster, self.cameras[view.id], points * 10, self.faces, size)
        result = {}
        for name in self.mode:
            support, values = observed[name]
            selected = support & drawn.valid
            overlap = selected.sum() / max(1, support.sum())
            if selected.sum() < 20:
                result[name] = {'cost': 1.25, 'coverage': float(overlap), 'pixels': int(selected.sum())}
                continue
            if name == 'depth':
                candidate = drawn.depth_cm[selected]
                measured = values[selected]
                if self.estimate:
                    # Product estimated camera has no depth origin or scale.
                    # Compare centered depth gradients at camera-relative scale.
                    candidate = candidate - np.median(candidate)
                    measured = measured - np.median(measured)
                errors = np.abs(candidate - measured)
                scale = CONFIG['depth_huber_cm']
                unit_name = 'cm'
            else:
                errors = angles(drawn.normals[selected], values[selected])
                scale = CONFIG['normal_huber_deg']
                unit_name = 'degrees'
            result[name] = {'cost': float(np.minimum(huber(errors / scale), 3.).mean() + .25 * (1 - overlap)),
                            'mean_error': float(errors.mean()), 'unit': unit_name,
                            'coverage': float(overlap), 'pixels': int(selected.sum())}
        return result

    def __call__(self, view, points, size):
        return sum(CONFIG[f'{name}_weight'] * term['cost']
                   for name, term in self.components(view, points, size).items())


def make_maps(raster, vertices, faces, views, cameras, reference, ref_faces, angles_by_id,
              predictions, rgb, body, estimated):
    oracle, learned, maps = {}, {}, {}
    for view in views:
        yaw = angles_by_id[view.id]
        exact_camera = Camera(yaw, **CONFIG['main_camera_cm'])
        target = visible_surface(raster, exact_camera, reference, ref_faces, SIZE)
        candidate = visible_surface(raster, cameras[view.id],
                                    observation_vertices(body, vertices, view) * 10, faces, SIZE)
        photo = sha256((rgb / f'{yaw}.png').read_bytes()).hexdigest()
        foreground = resized(view.mask.astype(np.uint8), SIZE).astype(bool)
        valid = target.valid & foreground
        maps[yaw] = target
        camera_source = view.source
        oracle[view.id] = {
            key: Evidence(photo, 'exact-geometry', 'G4 fixture', convention, (SIZE, SIZE), (SIZE, SIZE),
                          'identity, original RGB grid', target.mask, target.mask, valid, data,
                          camera_source, 'calibrated synthetic centimeters', 'ground truth')
            for key, data, convention in (('depth', target.depth_cm, 'positive camera Z, centimeters'),
                                          ('normal', target.normals, 'right/up/toward camera, outward'))}
        learned[view.id] = {}
        predicted_support = binary_erosion(foreground, iterations=3)
        depth_file = predictions / f'{yaw}-depth.npy'
        if depth_file.exists():
            raw = np.load(depth_file, allow_pickle=False)
            support = predicted_support & candidate.valid
            if support.sum() >= 20:
                inverse = affine_inverse(raw[support], candidate.depth_cm[support])
                aligned = aligned_depth(raw, *inverse)
                learned[view.id]['depth'] = Evidence(photo, 'Depth Anything V2 Small', '4472b7362082',
                            'relative inverse depth converted to D0 anchored camera depth', (SIZE, SIZE), (392, 392),
                            'cubic square resize, inverse affine alignment to D0', foreground, foreground,
                            predicted_support & np.isfinite(aligned), aligned, camera_source, 'D0 single global affine per view',
                            'predicted from RGB')
        normal_file = predictions / f'{yaw}-normal.npy'
        if normal_file.exists():
            data = dsine_to_camera(np.load(normal_file, allow_pickle=False))
            learned[view.id]['normal'] = Evidence(photo, 'DSINE', 'ef0c2afa32b4',
                          'right/up/toward camera', (SIZE, SIZE), (384, 384), 'DSINE forward-axis convention converted to physical outward',
                          foreground, foreground, predicted_support, data, camera_source, 'scale independent', 'predicted from RGB')
    return oracle, learned, maps
