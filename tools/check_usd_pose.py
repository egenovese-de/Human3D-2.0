# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify a directly imported target pose and a saved Blender round-trip."""
import json
from pathlib import Path
import sys

import bpy


def inspect():
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(rigs) != 1 or not meshes:
        raise RuntimeError("Expected a shared armature and at least one mesh.")
    rig = rigs[0]
    if not rig.animation_data or not rig.animation_data.action:
        raise RuntimeError("Target pose action missing after direct USD import.")
    bpy.context.scene.frame_set(1)
    graph = bpy.context.evaluated_depsgraph_get()
    deformations = {}
    for mesh in meshes:
        if not any(mod.type == "ARMATURE" and mod.object == rig for mod in mesh.modifiers):
            raise RuntimeError(f"Missing shared armature modifier: {mesh.name}")
        evaluated = mesh.evaluated_get(graph).data
        if len(evaluated.vertices) != len(mesh.data.vertices):
            raise RuntimeError(f"Vertex count changed: {mesh.name}")
        deformations[mesh.name] = max((a.co - b.co).length for a, b in zip(
            evaluated.vertices, mesh.data.vertices
        ))
    if max(deformations.values()) < 1e-5:
        raise RuntimeError("The target pose did not deform the imported mesh.")
    return {"action": rig.animation_data.action.name, "bones": len(rig.pose.bones),
            "max_deformation": deformations}


def main():
    source, output = map(Path, sys.argv[sys.argv.index("--") + 1:])
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=str(source.resolve()))
    before = inspect()
    blend = output / "roundtrip.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    after = inspect()
    if before != after:
        raise RuntimeError("Pose or mesh changed across Blender round-trip.")
    (output / "pose_check.json").write_text(
        json.dumps({"blender": bpy.app.version_string, "result": "PASS", **after}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
