"""Bake visible posed-mesh color into native UV space."""
from dataclasses import dataclass
from math import cos, radians, sin

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from .frozen_body import deform_vertices
from .native_rig import pose_transforms, skin_vertices, validate_rebind


@dataclass(frozen=True)
class Atlas:
    color: Image.Image
    coverage: Image.Image
    skin_candidate: Image.Image
    observed_fraction: float


def _samples(triangle, width, height):
    minimum = np.maximum(np.floor(triangle.min(axis=0)).astype(int), 0)
    maximum = np.minimum(np.ceil(triangle.max(axis=0)).astype(int), (width - 1, height - 1))
    if np.any(maximum < minimum):
        return None
    a, b, c = triangle
    u, v = b - a, c - a
    denominator = u[0] * v[1] - u[1] * v[0]
    if abs(denominator) < 1e-10:
        return None
    x, y = np.meshgrid(np.arange(minimum[0], maximum[0] + 1),
                       np.arange(minimum[1], maximum[1] + 1))
    dx, dy = x - a[0], y - a[1]
    b_weight = (dx * v[1] - dy * v[0]) / denominator
    c_weight = (u[0] * dy - u[1] * dx) / denominator
    a_weight = 1 - b_weight - c_weight
    inside = (a_weight >= -1e-7) & (b_weight >= -1e-7) & (c_weight >= -1e-7)
    if not inside.any():
        return None
    return x[inside], y[inside], np.column_stack((a_weight[inside], b_weight[inside], c_weight[inside]))


def _triangles(mesh):
    corners = []
    for face in mesh["faces"]:
        if face["group"] == "body":
            polygon = face["corners"]
            corners.extend((polygon[0], polygon[index], polygon[index + 1])
                           for index in range(1, len(polygon) - 1))
    return np.asarray(corners, dtype=int)


def _project_view(view, neutral, joints, rig, geometry, image_size, *, occluder=None):
    camera = view.alignment.camera
    if camera.horizontal_sign != 1:
        raise ValueError("Refit the photos with the M3 camera model before baking appearance.")
    posed = skin_vertices(neutral, rig["skin"], pose_transforms(rig, joints, view.alignment))
    yaw = radians(camera.yaw_degrees)
    forward = np.array((-sin(yaw), 0, cos(yaw)))
    depth = posed @ forward
    height, width = view.foreground.shape
    source_width, source_height = image_size
    projected = np.asarray([(point.real * width / source_width, point.imag * height / source_height)
                            for vertex in posed for point in (camera.project(vertex),)])
    z_buffer = np.full((height, width), -np.inf)

    def raster(image_points, depths, triangles):
        for indices in triangles:
            sample = _samples(image_points[indices], width, height)
            if sample is not None:
                x, y, bary = sample
                z_buffer[y, x] = np.maximum(z_buffer[y, x], bary @ depths[indices])

    raster(projected, depth, geometry)
    if occluder is not None:
        points, faces, skin = occluder
        posed_body = skin_vertices(points, skin, pose_transforms(rig, joints, view.alignment))
        body_projected = np.asarray([
            (pixel.real * width / source_width, pixel.imag * height / source_height)
            for vertex in posed_body for pixel in (camera.project(vertex),)
        ])
        raster(body_projected, posed_body @ forward, faces)
    norms = np.cross(posed[geometry[:, 1]] - posed[geometry[:, 0]],
                     posed[geometry[:, 2]] - posed[geometry[:, 0]])
    facing = np.clip(np.abs(norms @ forward) / np.maximum(np.linalg.norm(norms, axis=1), 1e-9), 0, 1)
    return projected, depth, z_buffer, facing


def bake_atlas(body, controls, views, target, *, size=512, garment=None):
    if target not in views or not 64 <= size <= 2048:
        raise ValueError("invalid_appearance_target_or_size")
    mesh, rig = body["mesh"], body["rig"]
    neutral = deform_vertices(body, controls)
    joints = validate_rebind(body, neutral)
    occluder = None
    if garment is not None:
        occluder = (neutral, _triangles(mesh)[:, :, 0], rig["skin"])
        neutral = garment.points
        mesh = {"texcoords": garment.uv, "faces": [{"group": "body", "corners": face} for face in garment.faces]}
        rig = rig | {"skin": garment.skin}
    triangles = _triangles(mesh)
    geometry, uv_indices = triangles[:, :, 0], triangles[:, :, 1]
    uv = np.asarray(mesh["texcoords"])
    uv = np.column_stack((uv[:, 0], 1 - uv[:, 1])) * (size - 1)
    atlas_pixels = [_samples(uv[indices], size, size) for indices in uv_indices]
    domain = np.zeros((size, size), dtype=bool)
    for sample in atlas_pixels:
        if sample is not None:
            domain[sample[1], sample[0]] = True
    color_sum = np.zeros((size, size, 3))
    weights = np.zeros((size, size))
    skin_sum = np.zeros_like(weights)
    target_view, _ = views[target]
    if not target_view.foreground.any():
        raise ValueError("appearance_target_has_no_foreground")
    target_light = np.median(target_view.rgb[target_view.foreground].mean(axis=1))
    for key, (view, image_size) in views.items():
        height, width = view.foreground.shape
        if not view.foreground.any():
            continue
        edge_distance = distance_transform_edt(view.foreground)
        projected, depth, z_buffer, facing = _project_view(view, neutral, joints, rig, geometry, image_size, occluder=occluder)
        intensity = np.median(view.rgb[view.foreground].mean(axis=1))
        gain = 1.0 if key == target else np.clip(target_light / max(intensity, 1), 0.7, 1.4)
        for index, sample in enumerate(atlas_pixels):
            if sample is None or facing[index] < 0.12:
                continue
            x, y, bary = sample
            points = np.rint(bary @ projected[geometry[index]]).astype(int)
            u, v = points[:, 0], points[:, 1]
            in_bounds = (0 <= u) & (u < width) & (0 <= v) & (v < height)
            u, v = np.clip(u, 0, width - 1), np.clip(v, 0, height - 1)
            z = bary @ depth[geometry[index]]
            front = np.isfinite(z_buffer[v, u]) & (z >= z_buffer[v, u] - 0.09)
            visible = in_bounds & front & view.foreground[v, u]
            if not visible.any():
                continue
            a, b = x[visible], y[visible]
            u, v = u[visible], v[visible]
            boundary_weight = np.clip(edge_distance[v, u] / 3, .25, 1)
            weight = boundary_weight * facing[index] ** 2 * (3.0 if key == target else 1.0)
            color_sum[b, a] += weight[:, None] * np.clip(view.rgb[v, u].astype(float) * gain, 0, 255)
            weights[b, a] += weight
            skin_sum[b, a] += weight * view.skin_candidate[v, u]
    observed = weights > 0
    if not observed.any():
        raise ValueError("No visible UV samples. Review the silhouette and alignment.")
    color = np.full((size, size, 3), 145, dtype=np.uint8)
    color[observed] = np.rint(color_sum[observed] / weights[observed, None]).astype(np.uint8)
    distances, nearest = distance_transform_edt(~observed, return_indices=True)
    padding = ~observed & (distances <= 4)
    color[padding] = color[tuple(nearest[:, padding])]
    coverage = np.zeros((size, size), dtype=np.uint8)
    coverage[domain & padding] = 96
    coverage[observed] = 255
    skin = np.zeros_like(coverage)
    skin[observed & (skin_sum > 0.75 * weights)] = 255
    return Atlas(Image.fromarray(color), Image.fromarray(coverage), Image.fromarray(skin),
                 np.count_nonzero(observed) / max(1, np.count_nonzero(domain)))

def neutralize_covered_body_color(body, atlas, garments):
    """Neutralize baked clothing color under covered body UV islands."""
    result = np.array(atlas.convert("RGB"))
    height, width = result.shape[:2]
    vertices = [set(garment.body_indices) for garment in garments]
    uv = np.asarray(body["mesh"]["texcoords"])
    uv = np.column_stack((uv[:, 0] * (width - 1), (1 - uv[:, 1]) * (height - 1)))
    for face in _triangles(body["mesh"]):
        if any(all(index in covered for index in face[:, 0]) for covered in vertices):
            sample = _samples(uv[face[:, 1]], width, height)
            if sample is not None:
                x, y, _ = sample
                result[y, x] = (145, 145, 145)
    return Image.fromarray(result)
