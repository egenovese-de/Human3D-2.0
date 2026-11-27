# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure collision at fixed garment parameters and validate virtual cap candidates."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np
from garment_collision import BVHTree, triangulate
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import CATEGORIES, measure_clearance, posed_garment, prototype
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session


def edges(face):
    return zip(face, (*face[1:], face[0]))


def inspect_closure(points, polygons):
    directed = Counter(edge for face in polygons for edge in edges(face))
    if any(n != 1 for n in directed.values()):
        return {"invalid": "edge direction duplicated"}
    boundary = [(a, b) for a, b in directed if (b, a) not in directed]
    cursor = dict(boundary)
    if len(cursor) != len(boundary) or set(cursor) != set(cursor.values()):
        return {"invalid": "boundary is not disjoint oriented loops"}
    loops = []
    while cursor:
        start = index = next(iter(cursor))
        loop = []
        while index in cursor:
            loop.append(index)
            index = cursor.pop(index)
        assert index == start
        loops.append(loop)
    base = triangulate(polygons)
    results = {}
    for method in ("centroid_fan", "polygon_tessellation"):
        vertices = points.tolist()
        triangles = list(base)
        for loop in loops:
            ring = list(reversed(loop))
            if method == "centroid_fan":
                center = len(vertices)
                vertices.append(points[ring].mean(axis=0).tolist())
                triangles.extend((a, b, center) for a, b in edges(ring))
            else:
                positions = [Vector(vertices[i]) for i in ring]
                triangles.extend(tuple(ring[i] for i in triangle) for triangle in tessellate_polygon([positions]))
        counts = Counter(edge for triangle in triangles for edge in edges(triangle))
        orientation_ok = all(n == 1 and counts[b, a] == 1 for (a, b), n in counts.items())
        xyz = np.asarray(vertices)[triangles]
        normals = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
        degenerate = int(np.sum(np.linalg.norm(normals, axis=1) < 1e-10))
        tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
        vertices_by_triangle = list(map(set, triangles))
        crossing = sum(a < b and not (vertices_by_triangle[a] & vertices_by_triangle[b])
                       for a, b in tree.overlap(tree))
        neighbors = defaultdict(list)
        for i, face in enumerate(triangles):
            for a, b in edges(face):
                neighbors[tuple(sorted((a, b)))].append(i)
        adjacency = defaultdict(set)
        for pair in neighbors.values():
            if len(pair) == 2:
                a, b = pair
                adjacency[a].add(b)
                adjacency[b].add(a)
        seen, pending = set(), [0]
        while pending:
            index = pending.pop()
            if index not in seen:
                seen.add(index)
                pending.extend(adjacency[index] - seen)
        connected = len(seen) == len(triangles)
        results[method] = {"loops": len(loops), "opposite_edge_pairs": orientation_ok,
                           "connected": connected, "degenerate_triangles": degenerate,
                           "nonadjacent_self_intersection_pairs": crossing,
                           "cap_screen_pass": bool(orientation_ok and connected and degenerate == 0 and crossing == 0)}
    return results


def run(previous, output):
    rows = []
    for identity in ("f_af01", "m_la01"):
        projects = {angle: next((previous / "holdout-native").glob(f"*_{identity}_bend{angle}-1")) / "project"
                    for angle in (0, 32)}
        body = load_project_body(Session(projects[0]).store)
        neutral = deform_vertices(body, {})
        rig = body["rig"]
        joints = rebind_joints(rig, neutral)
        faces = triangulate([tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"]
                             if face["group"] == "body"])
        for angle, project in projects.items():
            session = Session(project)
            target = session.shared_evidence().views[0].ref.photo_id
            alignment = session.current_shared_fit().alignments[target]
            matrices = pose_transforms(rig, joints, alignment)
            posed = skin_vertices(neutral, rig["skin"], matrices)
            body_tree = BVHTree.FromPolygons(posed.tolist(), faces, all_triangles=True)
            for category in CATEGORIES:
                shell = prototype(body, neutral, category)
                vertices = posed_garment(shell, matrices)
                polygons = [tuple(i for i, _ in face) for face in shell.faces]
                shell_tree = BVHTree.FromPolygons(vertices.tolist(), triangulate(polygons), all_triangles=True)
                clearance = measure_clearance(shell, body, posed, vertices)
                rows.append({"identity": identity, "target_bend_deg": angle, "pose": "native_estimate",
                             "category": category, "sampled_violations": clearance.violations,
                             "triangle_pairs": len(body_tree.overlap(shell_tree)),
                             "caps": inspect_closure(vertices, polygons)})
    output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
