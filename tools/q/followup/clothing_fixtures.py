# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent low-polygon garment controls and calibrated body/clothing masks."""
import argparse
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np


def mesh_object(scene, name, vertices, faces, color):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.color = (*color, 1)
    return obj


def tube(points, levels, ease, *, side=0, count=48):
    vertices, faces = [], []
    for z in levels:
        window = points[(np.abs(points[:, 2] - z) < .04) & (np.abs(points[:, 0]) < .29)]
        if side:
            window = window[window[:, 0] * side >= 0]
        low, high = np.quantile(window[:, :2], [.01, .99], axis=0)
        center = (low + high) / 2
        axes = (high - low) / 2 + ease
        for theta in np.linspace(0, 2 * np.pi, count, endpoint=False):
            x, y = center + axes * (math.cos(theta), math.sin(theta))
            vertices.append((float(x), float(y), float(z)))
    for ring in range(len(levels)-1):
        for i in range(count):
            a, b = ring*count+i, ring*count+(i+1)%count
            faces.append((a, b, b+count, a+count))
    return vertices, faces


def garment(points, height, spec):
    geometry, faces = [], []
    for low, high, ease, side in spec:
        v, f = tube(points, np.linspace(low*height, high*height, 12), ease, side=side)
        faces.extend(tuple(i+len(geometry) for i in face) for face in f)
        geometry.extend(v)
    return geometry, faces


def triangulate(faces):
    return [(face[0], face[i], face[i+1]) for face in faces for i in range(1, len(face)-1)]


def run(dataset, output, report):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_shadows = False
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.16
    specs = {
        "bare": [],
        "top": [[(.58,.82,.018,0)]],
        "shorts": [[(.49,.59,.02,0),(.37,.51,.014,1),(.37,.51,.014,-1)]],
        "trousers": [[(.49,.59,.02,0),(.09,.51,.018,1),(.09,.51,.018,-1)]],
        "loose": [[(.44,.82,.065,0)]],
        "layered": [[(.58,.82,.018,0)],[(.54,.83,.045,0)]],
    }
    rows = []
    for identity in ("f_af01", "m_la01"):
        folder = dataset / f"{identity}_neutral"
        original = json.loads((folder / "mesh.json").read_text())
        points = np.asarray(original["vertices"])
        height = np.ptp(points[:, 2])
        body = mesh_object(scene, "Body", points.tolist(), original["faces"], (.48,.27,.18))
        body_tree = BVHTree.FromPolygons(points.tolist(), triangulate(original["faces"]), all_triangles=True)
        center = Vector((0, 0, height / 2))
        for label, specification in specs.items():
            destination = output / identity / label
            destination.mkdir(parents=True, exist_ok=True)
            objects, metrics = [], []
            for index, layer in enumerate(specification):
                vertices, faces = garment(points, height, layer)
                name = f"layer_{index}"
                obj = mesh_object(scene, name, vertices, faces, ((.10,.23,.55),(.53,.22,.13))[index])
                objects.append(obj)
                tri = triangulate(faces)
                tree = BVHTree.FromPolygons(vertices, tri, all_triangles=True)
                intersections = body_tree.overlap(tree)
                samples = []
                for p in vertices:
                    location, normal, _, _ = body_tree.find_nearest(Vector(p))
                    samples.append(float((Vector(p)-location).dot(normal)) * 1000)
                metrics.append({"layer": name, "faces": len(tri), "vertices": len(vertices),
                                "body_surface_intersecting_triangle_pairs": len(intersections),
                                "intersecting_garment_triangles": len({b for _, b in intersections}),
                                "sample_vertex_signed_min_mm": min(samples),
                                "sample_vertex_signed_negative": sum(value < -.1 for value in samples),
                                "sample_vertex_signed_p05_mm": float(np.quantile(samples, .05)),
                                "volume": None, "volume_exclusion": "open hem boundaries"})
                (destination / (name+".json")).write_text(json.dumps(dict(vertices=vertices, faces=faces)))
            for yaw in (0, 90):
                angle = math.radians(yaw)
                camera.location = center + Vector((4*math.sin(angle), -4*math.cos(angle), 0))
                camera.rotation_euler = (center-camera.location).to_track_quat("-Z","Y").to_euler()
                for mode in ("composite", "body_only", *(f"layer_{i}" for i in range(len(objects)))):
                    body.hide_render = mode not in {"composite","body_only"}
                    for i, obj in enumerate(objects):
                        obj.hide_render = mode not in {"composite",f"layer_{i}"}
                    scene.render.filepath = str((destination / f"{mode}-{yaw}.png").resolve())
                    bpy.ops.render.render(write_still=True)
            rows.append(dict(identity=identity, treatment=label, independent_layers=metrics))
            for obj in objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.objects.remove(body, do_unlink=True)
    report.write_text(json.dumps(rows, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("dataset", "output", "report"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
