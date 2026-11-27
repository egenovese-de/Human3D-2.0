# SPDX-License-Identifier: GPL-3.0-or-later
"""Use independently ray-rendered analytic colors to test the native UV baker."""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path

import bpy  # Initializes Blender mathutils in the module distribution.
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np
from scipy.ndimage import shift

from human3d.alignment import Alignment, Camera
from human3d.appearance import AppearanceView
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.session import Session
from human3d.texture_bake import bake_atlas


IMAGE = 256
ATLAS = 256
OCCLUDER = np.array([241, 17, 229])


def colors(points):
    x, y, z = np.asarray(points).T
    stripes = (np.floor((y + 9) * 1.5) % 2) * 70
    rgb = np.column_stack((105 + stripes + 15*np.sin(x),
        110 + 47*np.cos(z*2), 115 + 60*np.sin(x*2+y*.8)))
    chart = (np.abs(x)<.9) & (y>1.5) & (y<3.5) & (z>0)
    reference_patches = np.array(((192,57,52),(65,153,87),(56,92,190),(181,153,74)))
    rgb[chart] = reference_patches[2*(x[chart]>0)+(y[chart]>2.5)]
    return np.uint8(np.rint(rgb))


def camera_data(yaw):
    angle = np.radians(yaw)
    return np.array((np.cos(angle), 0, np.sin(angle))), np.array((-np.sin(angle), 0, np.cos(angle)))


def render(tree, yaw, exposure=1, occlude=False):
    right, depth = camera_data(yaw)
    pixel_scale = 13
    camera = Camera(yaw, pixel_scale, complex(128, 128), 1)
    points = np.zeros((IMAGE, IMAGE, 3))
    visible = np.zeros((IMAGE, IMAGE), dtype=bool)
    for y in range(IMAGE):
        for x in range(IMAGE):
            point = 50*depth + right*(x-128)/pixel_scale + np.array((0, (128-y)/pixel_scale, 0))
            hit = tree.ray_cast(Vector(point), Vector(-depth))[0]
            if hit is not None:
                visible[y, x] = True
                points[y, x] = hit
    rgb = np.full(visible.shape + (3,), 224, dtype=np.uint8)
    rgb[visible] = np.uint8(np.clip(np.rint(colors(points[visible]) * exposure), 0, 255))
    if occlude:
        rgb[94:137, 118:145] = OCCLUDER
    return AppearanceView(rgb, visible, np.zeros_like(visible), Alignment(camera, 0, {}))


def seam_stats(geometry, charts, uv, atlas):
    copies = {}
    for face, chart in zip(geometry, charts):
        for a, b in ((0,1),(1,2),(2,0)):
            if face[a] > face[b]:
                a,b = b,a
            copies.setdefault((face[a],face[b]),set()).add((chart[a],chart[b]))
    rgb, observed = np.asarray(atlas.color,dtype=float), np.asarray(atlas.coverage)==255
    deltas = []
    candidate_edges = 0
    for pairs in copies.values():
        if len(pairs) != 2:
            continue
        candidate_edges += 1
        first, second = (uv[list(edge)] for edge in sorted(pairs))
        for t in (.25,.5,.75):
            a,b = (np.rint((1-t)*edge[0]+t*edge[1]).astype(int) for edge in (first,second))
            if observed[a[1],a[0]] and observed[b[1],b[0]]:
                deltas.append(float(np.abs(rgb[a[1],a[0]]-rgb[b[1],b[0]]).mean()))
    return dict(candidate_seam_edges=candidate_edges, paired_observed_seam_samples=len(deltas),
                observed_seam_rgb_mae=float(np.mean(deltas)) if deltas else None)


def run(project, work, output, *, m6_diagnostics=False):
    work.mkdir(parents=True, exist_ok=True)
    body = load_project_body(Session(project).store)
    points = np.asarray(deform_vertices(body, {}))
    faces = [face["corners"] for face in body["mesh"]["faces"] if face["group"] == "body"]
    tri = np.asarray([(face[0], face[i], face[i+1]) for face in faces for i in range(1, len(face)-1)])
    uv = np.asarray(body["mesh"]["texcoords"])
    geometry, charts = tri[:, :, 0], tri[:, :, 1]
    tree = BVHTree.FromPolygons(points.tolist(), geometry.tolist(), all_triangles=True)
    zero = render(tree, 0)
    reverse = render(tree, 180)
    dim = render(tree, 45, .8)
    same_dim = render(tree, 45)
    contaminant = render(tree, 0, occlude=True)
    gated = contaminant.foreground.copy()
    gated[94:137, 118:145] = False
    masked = AppearanceView(contaminant.rgb, gated, contaminant.skin_candidate, contaminant.alignment)
    shifted = AppearanceView(shift(zero.rgb, (0, 3, 0), order=0).astype(np.uint8), zero.foreground,
                             zero.skin_candidate, zero.alignment)

    # Sample independent triangle interiors at the texel centres of their own charts.
    ideal_uv = np.column_stack((uv[:, 0], 1 - uv[:, 1])) * (ATLAS - 1)
    coords = ideal_uv[charts]
    centers = np.rint(coords.mean(axis=1)).astype(int)
    z = centers - coords[:, 0]
    a, b = coords[:, 1] - coords[:, 0], coords[:, 2] - coords[:, 0]
    cross = lambda m, n: m[:, 0]*n[:, 1]-m[:, 1]*n[:, 0]
    den = cross(a, b)
    den[np.abs(den) < 1e-10] = np.nan
    t, u = cross(z, b) / den, cross(a, z) / den
    interior = (t > .12) & (u > .12) & (1-t-u > .12)
    bary = np.column_stack((1-t-u, t, u))[interior]
    xyz = np.einsum("ij,ijk->ik", bary, points[geometry[interior]])
    px, py = centers[interior].T
    hidden = []
    for p in xyz:
        hit = tree.ray_cast(Vector((p[0], p[1], 50)), Vector((0, 0, -1)))[0]
        hidden.append(hit is None or abs(hit.z - p[2]) > .03)
    hidden = np.array(hidden)
    expected = colors(xyz)
    refs = {"clean_front": [zero], "clean_front_rear": [zero, reverse],
            "front_side_clean": [zero, same_dim], "front_side_dimmed": [zero, dim],
            "unmasked_occluder": [contaminant], "masked_occluder": [masked],
            "horizontal_shift_three_px": [shifted]}
    if m6_diagnostics:
        refs["horizontal_shift_one_px"] = [replace(zero, rgb=shift(zero.rgb, (0, 1, 0), order=0).astype(np.uint8))]
        for pixels in (1, 3):
            moved = replace(zero.alignment.camera, origin=zero.alignment.camera.origin + pixels)
            refs[f"projected_camera_shift_{pixels}_px"] = [
                replace(zero, alignment=replace(zero.alignment, camera=moved))
            ]
    rows = []
    for name, inputs in refs.items():
        views = {i: (value, (IMAGE, IMAGE)) for i, value in enumerate(inputs)}
        atlas = bake_atlas(body, {}, views, 0, size=ATLAS)
        atlas.color.save(work / (name+".png"))
        atlas.coverage.save(work / (name+"-coverage.png"))
        color = np.asarray(atlas.color)[py, px]
        coverage = np.asarray(atlas.coverage)[py, px]
        observed = coverage == 255
        visible = observed & ~hidden
        delta = np.abs(color.astype(float)-expected)
        rows.append(dict(condition=name, tested_triangle_interiors=len(xyz), front_visible_samples=int((~hidden).sum()),
                         visible_observed_samples=int(visible.sum()), visible_rgb_mae=float(delta[visible].mean()),
                         front_hidden_samples=int(hidden.sum()), front_hidden_observed=int((hidden & observed).sum()),
                         occluder_color_observed_samples=int((np.linalg.norm(color.astype(float)-OCCLUDER, axis=1)<5).sum()),
                         coverage_fraction=atlas.observed_fraction, padded_samples=int((coverage==96).sum()),
                         default_unobserved_samples=int((coverage==0).sum()),
                         **seam_stats(geometry, charts, ideal_uv, atlas)))
        if m6_diagnostics:
            rows[-1]["alignment_diagnostics"] = {key: asdict(value) for key, value in atlas.view_diagnostics.items()}
    output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("project", "work", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--m6-diagnostics", action="store_true")
    run(**vars(parser.parse_args()))
