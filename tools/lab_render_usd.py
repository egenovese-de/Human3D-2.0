"""Headless Blender USD preview renderer for the isolated lab/render branch.

Usage:
  blender --background --python tools/lab_render_usd.py -- --input path/to/asset.usdz --out-dir path/to/output
Does not alter or save the source USD and does not modify Human3D project state.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--framing", type=Path, help="Use camera center and span from another render report.")
    parser.add_argument("--label", default="USD asset preview (not empirical validation)")
    return parser.parse_args(args)


def configure_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.render.resolution_x = 768
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("LAB_World")
    scene.world.color = (0.12, 0.12, 0.12)
    return scene


def scene_bounds(meshes):
    coords = [obj.matrix_world @ Vector(corner)
              for obj in meshes for corner in obj.bound_box]
    mins = Vector((min(p[i] for p in coords) for i in range(3)))
    maxs = Vector((max(p[i] for p in coords) for i in range(3)))
    center = (mins + maxs) / 2
    span = max(maxs[i] - mins[i] for i in range(3))
    if not math.isfinite(span) or span <= 1e-6:
        raise RuntimeError("Imported asset has invalid or degenerate bounds")
    return center, span, tuple(mins), tuple(maxs)


def point_camera(scene, center, span, name, direction):
    data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, data)
    scene.collection.objects.link(camera)
    offset = Vector(direction).normalized() * span * 2.0
    camera.location = center + offset
    direction_vector = center - camera.location
    camera.rotation_euler = direction_vector.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = span * 1.5
    scene.camera = camera
    return camera


def lighting(scene, center, span):
    for name, direction, power in (
        ("Key", (1, -2, 3), 1100),
        ("Fill", (-2, -1, 1), 650),
        ("Rim", (0, 2, 2), 1000),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power * max(0.1, span / 2) ** 2
        data.shape = "DISK"
        data.size = max(0.5, span * 1.2)
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = center + Vector(direction) * span
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_views(scene, center, span, output, prefix):
    # Blender uses Z-up after USD import. Orthographic viewpoints.
    for name, direction in (
        ("front", (0, -1.0, 0.25)),
        ("three_quarter", (1.0, -1.0, 0.3)),
        ("side", (1.0, 0, 0.25)),
        ("back", (0, 1.0, 0.25)),
    ):
        camera = point_camera(scene, center, span, f"Camera_{name}", direction)
        scene.render.filepath = str(output / f"{prefix}_{name}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)


def main():
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(f"USD asset missing: {args.input}")
    if args.input.suffix.lower() not in {".usd", ".usda", ".usdc", ".usdz"}:
        raise ValueError("Input must be an OpenUSD asset")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scene = configure_scene()
    result = bpy.ops.wm.usd_import(filepath=str(args.input.resolve()))
    if "FINISHED" not in result:
        raise RuntimeError(f"USD import failed: {result}")
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("No renderable mesh in USD asset")
    center, span, bounds_min, bounds_max = scene_bounds(meshes)
    if args.framing:
        frame = json.loads(args.framing.read_text(encoding="utf-8"))
        center, span = Vector(frame["camera_center"]), float(frame["bounding_span"])
    lighting(scene, center, span)
    render_views(scene, center, span, args.out_dir, "textured")
    clay = bpy.data.materials.new("LAB_ONLY_Clay_Override")
    clay.diffuse_color = (0.69, 0.73, 0.77, 1.0)
    clay.use_nodes = True
    bsdf = clay.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = clay.diffuse_color
    scene.view_layers[0].material_override = clay
    render_views(scene, center, span, args.out_dir, "clay")
    (args.out_dir / "render_report.json").write_text(
        json.dumps({
            "label": args.label, "source_asset": args.input.name,
            "mesh_count": len(meshes),
            "mesh_names": [obj.name for obj in meshes],
            "bounds_min": bounds_min, "bounds_max": bounds_max,
            "bounding_span": span, "camera_center": tuple(center), "blender_version": bpy.app.version_string,
            "note": "Visual smoke/inspection render only; no photographic reconstruction quality PASS."
        }, indent=2),
        encoding="utf-8",
    )
    print("LAB_RENDER_PASS", args.out_dir)


if __name__ == "__main__":
    main()
