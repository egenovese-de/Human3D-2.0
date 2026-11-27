"""Blender-side controlled USD inspection and round-trip."""
import argparse
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab_render_usd import scene_bounds, lighting, render_views

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
    scene=bpy.context.scene
    meshes=[o for o in scene.objects if o.type=="MESH"]
    center,span,mins,maxs=scene_bounds(meshes)
    scene.render.engine="CYCLES"
    scene.cycles.samples=8
    scene.render.resolution_x=384
    scene.render.resolution_y=480
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.world=bpy.data.worlds.new("LAB_World")
    scene.world.color=(0.12,0.12,0.12)
    lighting(scene,center,span)
    render_views(scene,center,span,a.output,"textured")
    clay=bpy.data.materials.new("LAB_Clay")
    clay.use_nodes=True
    clay.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value=(0.69,0.73,0.77,1)
    scene.view_layers[0].material_override=clay
    render_views(scene,center,span,a.output,"clay")
    (a.output/"render_report.json").write_text(json.dumps({"center":list(center),"span":span,"bounds_min":mins,"bounds_max":maxs,"resolution":[384,480],"samples":8,"views":["front","back","side","three_quarter"],"textured_mode":"imported materials; texture presence not guaranteed"},indent=2))
    (a.output/"blender_metrics.json").write_text(json.dumps({"before":before,"after":after,"version":bpy.app.version_string},indent=2))
if __name__=="__main__":
    main()
