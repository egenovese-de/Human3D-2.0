"""Blender-side controlled USD inspection and round-trip."""
import argparse
import json
from pathlib import Path
import sys
import bpy

def inspect():
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    return {"meshes":len(meshes),"vertices":sum(len(o.data.vertices) for o in meshes),"faces":sum(len(o.data.polygons) for o in meshes),"armatures":sum(o.type=="ARMATURE" for o in bpy.context.scene.objects),"skinned_meshes":sum(any(m.type=="ARMATURE" for m in o.modifiers) for o in meshes)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    if a.input.suffix.lower() not in (".usd",".usda",".usdc",".usdz"):
        raise ValueError("USD input required")
    a.output.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if "FINISHED" not in bpy.ops.wm.usd_import(filepath=str(a.input.resolve())):
        raise RuntimeError("USD import failed")
    before=inspect()
    if not before["meshes"] or not before["vertices"]:
        raise RuntimeError("empty geometry")
    path=str((a.output/"scene.blend").resolve())
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    after=inspect()
    if before!=after:
        raise RuntimeError("round-trip mismatch")
    (a.output/"blender_metrics.json").write_text(json.dumps({"before":before,"after":after,"version":bpy.app.version_string},indent=2))
if __name__=="__main__":
    main()
