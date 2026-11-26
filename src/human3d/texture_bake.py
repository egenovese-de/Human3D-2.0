"""Bake visible posed-mesh color into native UV space."""
from dataclasses import dataclass
from math import cos, radians, sin

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from .frozen_body import deform_vertices
from .native_rig import pose_transforms, skin_vertices, validate_rebind, validate_pose


@dataclass(frozen=True)
class Atlas:
    color: Image.Image
    coverage: Image.Image
    skin_candidate: Image.Image
    observed_fraction: float
    hair_candidate: Image.Image | None = None


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
    if not corners:
        raise ValueError("missing_texture_topology")
    return np.asarray(corners, dtype=int)


def _project_view(view, neutral, joints, rig, geometry, image_size, *, occluder=None):
    camera = view.alignment.camera
    if camera.horizontal_sign != 1:
        raise ValueError("Refit the photos with the M3 camera model before baking appearance.")
    posed = skin_vertices(neutral, rig["skin"], pose_transforms(rig, joints, view.alignment))
    if not np.isfinite(posed).all():
        raise ValueError("invalid_texture_pose")
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


def _blend_observed_seams(color, observed, geometry, uv_indices, uv):
    """Match observed texels on both UV copies of a shared geometric edge."""
    edges = {}
    for vertices, corners in zip(geometry, uv_indices):
        for first, last in ((0, 1), (1, 2), (2, 0)):
            if vertices[first] > vertices[last]:
                first, last = last, first
            edge = (vertices[first], vertices[last])
            edges.setdefault(edge, set()).add((corners[first], corners[last]))
    blended = color.astype(float)
    counts = np.ones(observed.shape, dtype=float)
    height, width = observed.shape
    for copies in edges.values():
        if len(copies) != 2:
            continue
        first, second = (uv[list(pair)] for pair in sorted(copies))
        samples = max(2, int(max(np.linalg.norm(edge[1] - edge[0]) for edge in (first, second))) + 1)
        t = np.linspace(0, 1, samples)[:, None]
        a = np.rint(first[0] * (1 - t) + first[1] * t).astype(int)
        b = np.rint(second[0] * (1 - t) + second[1] * t).astype(int)
        a, b = (np.clip(points, (0, 0), (width - 1, height - 1)) for points in (a, b))
        ax, ay = a.T
        bx, by = b.T
        keep = observed[ay, ax] & observed[by, bx]
        ax, ay, bx, by = (axis[keep] for axis in (ax, ay, bx, by))
        np.add.at(blended, (ay, ax), color[by, bx])
        np.add.at(blended, (by, bx), color[ay, ax])
        np.add.at(counts, (ay, ax), 1)
        np.add.at(counts, (by, bx), 1)
    return np.rint(blended / counts[:, :, None]).astype(np.uint8)


def _hidden_vertices(rig, regions):
    """Exclude strongly region-bound vertices from hidden-region color sampling."""
    prefixes = {"left_arm": ("upperarm", "lowerarm", "wrist", "finger"),
                "right_arm": ("upperarm", "lowerarm", "wrist", "finger"),
                "left_leg": ("upperleg", "lowerleg", "foot", "toe"),
                "right_leg": ("upperleg", "lowerleg", "foot", "toe"),
                "face": ("head", "jaw", "eye", "tongue"),
                "torso": ("spine", "pelvis", "chest", "breast", "clavicle")}
    blocked_bones = set()
    for region in regions:
        if region not in prefixes:
            continue
        side = ".L" if region.startswith("left") else ".R" if region.startswith("right") else None
        blocked_bones.update(bone for bone in rig["bones"]
                             if bone.startswith(prefixes[region]) and (side is None or bone.endswith(side)))
    return {i for i, influences in enumerate(rig["skin"])
            if sum(influences.get(bone, 0) for bone in blocked_bones) > .7}


def _validate_view(view, image_size):
    foreground = view.foreground
    if (foreground.ndim != 2 or not foreground.size or foreground.dtype != np.bool_
            or view.rgb.shape != (*foreground.shape, 3) or view.rgb.dtype != np.uint8
            or view.skin_candidate.shape != foreground.shape or view.skin_candidate.dtype != np.bool_
            or (view.hair_candidate is not None and
                (view.hair_candidate.shape != foreground.shape or view.hair_candidate.dtype != np.bool_))
            or len(image_size) != 2 or not all(np.isfinite(v) and v > 0 for v in image_size)):
        raise ValueError("invalid_appearance_view")


def bake_atlas(body, controls, views, target, *, size=512, garment=None):
    if target not in views or type(size) is not int or not 64 <= size <= 2048:
        raise ValueError("invalid_appearance_target_or_size")
    for view, image_size in views.values():
        _validate_view(view, image_size)
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
    uv = np.asarray(mesh["texcoords"], dtype=float)
    if uv.ndim != 2 or uv.shape[1] != 2 or not np.isfinite(uv).all() or np.any((uv < 0) | (uv > 1)):
        raise ValueError("invalid_texture_uv")
    uv = np.column_stack((uv[:, 0], 1 - uv[:, 1])) * (size - 1)
    atlas_pixels = [_samples(uv[indices], size, size) for indices in uv_indices]
    domain = np.zeros((size, size), dtype=bool)
    for sample in atlas_pixels:
        if sample is not None:
            domain[sample[1], sample[0]] = True
    color_sum = np.zeros((size, size, 3))
    weights = np.zeros((size, size))
    skin_sum = np.zeros_like(weights)
    hair_sum = np.zeros_like(weights)
    head_vertices = np.asarray([sum(weight for name, weight in influences.items()
                                    if name.startswith(("head", "jaw")) or name == "neck")
                                for influences in rig["skin"]])
    target_view, _ = views[target]
    if not target_view.foreground.any():
        raise ValueError("appearance_target_has_no_foreground")
    target_light = np.median(target_view.rgb[target_view.foreground].mean(axis=1))
    for key in (target, *sorted(key for key in views if key != target)):
        view, image_size = views[key]
        view_colors = np.zeros_like(color_sum)
        view_weights = np.zeros_like(weights)
        height, width = view.foreground.shape
        if not view.foreground.any():
            continue
        if garment is None:
            posed = skin_vertices(neutral, rig["skin"], pose_transforms(rig, joints, view.alignment))
            validate_pose(body, neutral, posed)
        edge_distance = distance_transform_edt(view.foreground)
        projected, depth, z_buffer, facing = _project_view(view, neutral, joints, rig, geometry, image_size, occluder=occluder)
        intensity = np.median(view.rgb[view.foreground].mean(axis=1))
        gain = 1.0 if key == target else np.clip(target_light / max(intensity, 1), 0.7, 1.4)
        blocked = _hidden_vertices(rig, view.hidden_regions)
        for index, sample in enumerate(atlas_pixels):
            if sample is None or facing[index] < 0.12 or (blocked and all(i in blocked for i in geometry[index])):
                continue
            x, y, bary = sample
            points = np.rint(bary @ projected[geometry[index]]).astype(int)
            u, v = points[:, 0], points[:, 1]
            in_bounds = (0 <= u) & (u < width) & (0 <= v) & (v < height)
            u, v = np.clip(u, 0, width - 1), np.clip(v, 0, height - 1)
            z = bary @ depth[geometry[index]]
            # One pixel of sampling ambiguity in model units, bounded to
            # avoid assigning a foreground limb to a nearby hidden surface.
            pixel_scale = abs(view.alignment.camera.similarity) * min(width / image_size[0],
                                                                       height / image_size[1])
            tolerance = np.clip(.7 / max(pixel_scale * facing[index], 1e-6), .02, .09)
            front = np.isfinite(z_buffer[v, u]) & (z >= z_buffer[v, u] - tolerance)
            visible = in_bounds & front & view.foreground[v, u]
            if not visible.any():
                continue
            if garment is None and view.hair_candidate is not None:
                scalp = bary @ head_vertices[geometry[index]] >= .5
                visible &= ~view.hair_candidate[v, u] | scalp
                if not visible.any():
                    continue
            a, b = x[visible], y[visible]
            u, v = u[visible], v[visible]
            boundary_weight = np.clip(edge_distance[v, u] / 3, .25, 1)
            weight = boundary_weight * facing[index] ** 2 * (3.0 if key == target else 1.0)
            view_colors[b, a] += weight[:, None] * view.rgb[v, u]
            view_weights[b, a] += weight
            skin_sum[b, a] += weight * view.skin_candidate[v, u]
            if garment is None and view.hair_candidate is not None:
                hair_sum[b, a] += weight * view.hair_candidate[v, u]
        if key == target:
            target_colors, target_weights = view_colors, view_weights
        else:
            overlap = (view_weights > .1) & (target_weights > .3)
            if np.count_nonzero(overlap) >= 64:
                target_samples = (target_colors[overlap] / target_weights[overlap, None]).mean(axis=1)
                current_samples = (view_colors[overlap] / view_weights[overlap, None]).mean(axis=1)
                valid = (current_samples > 24) & (target_samples > 24)
                if np.count_nonzero(valid) >= 64:
                    gain = np.clip(np.median(target_samples[valid] / current_samples[valid]), .7, 1.4)
        color_sum += np.minimum(view_colors * gain, 255 * view_weights[:, :, None])
        weights += view_weights
    observed = weights > 0
    if not observed.any():
        raise ValueError("No visible UV samples. Review the silhouette and alignment.")
    color = np.full((size, size, 3), 145, dtype=np.uint8)
    color[observed] = np.rint(color_sum[observed] / weights[observed, None]).astype(np.uint8)
    color = _blend_observed_seams(color, observed, geometry, uv_indices, uv)
    distances, nearest = distance_transform_edt(~observed, return_indices=True)
    padding = ~observed & (distances <= 4)
    color[padding] = color[tuple(nearest[:, padding])]
    coverage = np.zeros((size, size), dtype=np.uint8)
    coverage[domain & padding] = 96
    coverage[observed] = 255
    skin = np.zeros_like(coverage)
    skin[observed & (skin_sum > 0.75 * weights)] = 255
    hair = (observed & (hair_sum > .75 * weights)).astype(np.uint8) * 255
    return Atlas(Image.fromarray(color), Image.fromarray(coverage), Image.fromarray(skin),
                 np.count_nonzero(observed) / max(1, np.count_nonzero(domain)), Image.fromarray(hair))

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
