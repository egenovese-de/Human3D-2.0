"""Floating-point visible surface observations in G4 camera coordinates."""
from dataclasses import dataclass
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import binary_erosion

CONFIG = json.loads(Path(__file__).with_name('config.json').read_text())
SIZE = CONFIG['image_size']


@dataclass(frozen=True)
class Surface:
    mask: np.ndarray
    depth_cm: np.ndarray
    normals: np.ndarray
    triangle: np.ndarray
    valid: np.ndarray


@dataclass(frozen=True)
class Evidence:
    photo_sha256: str
    model: str
    revision: str
    convention: str
    original_size: tuple[int, int]
    inference_size: tuple[int, int]
    image_transform: str
    foreground: np.ndarray
    visibility: np.ndarray
    valid: np.ndarray
    values: np.ndarray
    camera_source: str
    scale_source: str
    provenance: str
    confidence: np.ndarray | None = None
    uncertainty: float | None = None


def unit(value):
    return value / np.maximum(np.linalg.norm(value, axis=-1, keepdims=True), 1e-12)


def face_normals(vertices, faces):
    triangles = vertices[faces]
    return unit(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]))


def visible_surface(raster, camera, vertices, faces, size):
    projected = camera.project(vertices, size)
    if np.any((projected[:, 2] <= 10) | (projected[:, 2] >= 10000)):
        raise ValueError('Geometry outside admitted [10, 10000] cm clipping interval')
    mask, depth, ids = raster.draw(camera, vertices, faces, size, channels=True)
    normals = np.zeros((*ids.shape, 3), np.float32)
    normals[mask] = face_normals(vertices, faces)[ids[mask]] @ camera.axes().T
    ray = np.broadcast_to([0., 0., 1.], normals.shape)
    if camera.perspective:
        yy, xx = np.indices(ids.shape) + .5
        focal = size * camera.distance / camera.span
        ray = np.stack((-(xx - size * (.5 + camera.dx)) / focal,
                        (yy - size * (.5 + camera.dy)) / focal, np.ones_like(xx)), axis=-1)
    interior = binary_erosion(mask, iterations=max(1, round(size / 160)))
    valid = interior & ((ray * normals).sum(axis=-1) > .08)
    return Surface(mask, depth, normals, ids, valid)


def resized(values, size, interpolation=cv2.INTER_NEAREST_EXACT):
    return cv2.resize(values, (size, size), interpolation=interpolation)


def perspective_normals(depth, camera):
    size = len(depth)
    yy, xx = np.indices(depth.shape) + .5
    focal = size * camera.distance / camera.span
    xyz = np.stack(((xx - size * (.5 + camera.dx)) * depth / focal,
                    -(yy - size * (.5 + camera.dy)) * depth / focal, -depth), -1)
    du = (xyz[1:-1, 2:] - xyz[1:-1, :-2]) * .5
    dv = (xyz[2:, 1:-1] - xyz[:-2, 1:-1]) * .5
    return unit(np.cross(dv, du))


def affine_inverse(predicted, target_cm):
    values = np.asarray(predicted, np.float64)
    target = 1 / np.asarray(target_cm, np.float64)
    centered = values - values.mean()
    slope = max(0., float(np.dot(centered, target - target.mean()) /
                          max(1e-12, np.dot(centered, centered))))
    return slope, float(target.mean() - slope * values.mean())


def aligned_depth(prediction, slope, offset):
    inverse = slope * prediction + offset
    result = np.full(prediction.shape, np.inf, np.float32)
    np.divide(1., inverse, where=inverse > 1e-5, out=result)
    return result


def angles(first, second):
    return np.rad2deg(np.arccos(np.clip(np.sum(first * second, axis=-1), -1, 1)))


def huber(values):
    magnitude = np.abs(values)
    return np.where(magnitude <= 1, .5 * magnitude ** 2, magnitude - .5)


def dsine_to_camera(stored):
    """Convert the stored DSINE output to physical outward G4 normals.

    DSINE's target construction uses positive-Z ray-facing orientation in
    the right/down/forward projection frame. Reverse that vector for
    physical outward in that frame, then change Y and Z basis signs.
    Cached predictor arrays already carry the initial Y basis reflection.
    """
    return stored * np.array([-1., -1., 1.], np.float32)
