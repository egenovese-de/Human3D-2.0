# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender-side controlled USD inspection and round-trip."""
import argparse
import json
from pathlib import Path
import sys
import bpy
import math
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab_render_usd import scene_bounds, lighting, render_views

def inspect():
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    rigs=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    weighted=sum(bool(v.groups) for o in meshes for v in o.data.vertices)
    return {"bones":sum(len(o.data.bones) for o in rigs),"weighted_vertices":weighted,"meshes":len(meshes),"vertices":sum(len(o.data.vertices) for o in meshes),"faces":sum(len(o.data.polygons) for o in meshes),"armatures":sum(o.type=="ARMATURE" for o in bpy.context.scene.objects),"skinned_meshes":sum(any(m.type=="ARMATURE" for m in o.modifiers) for o in meshes)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--framing",type=Path)
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
    bpy.ops.file.pack_all()
    path=str((a.output/"scene.blend").resolve())
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    after=inspect()
    if a.input.name=="human.usdz" and not all(after[k]>0 for k in ("bones","weighted_vertices","armatures","skinned_meshes")):
        raise RuntimeError("human skinning missing")
    if before!=after:
        raise RuntimeError("round-trip mismatch")
    scene=bpy.context.scene
    meshes=[o for o in scene.objects if o.type=="MESH"]
    center,span,mins,maxs=scene_bounds(meshes)
    if a.framing:
        frame=json.loads(a.framing.read_text())
        center,span=Vector(frame["center"]),float(frame["span"])
        if len(center)!=3 or not all(math.isfinite(v) for v in center) or not math.isfinite(span) or span<=0:
            raise ValueError("invalid shared framing")
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
    scene.view_layers[0].material_override=None
    wire=bpy.data.materials.new("LAB_Wire")
    wire.use_nodes=True
    wire.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value=(0.08,0.08,0.08,1)
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(wire)
        mod=obj.modifiers.new("LAB_Wireframe","WIREFRAME")
        mod.thickness=span*0.002
        mod.use_replace=True
    render_views(scene,center,span,a.output,"wireframe")
    (a.output/"render_report.json").write_text(json.dumps({"center":list(center),"span":span,"bounds_min":mins,"bounds_max":maxs,"resolution":[384,480],"samples":8,"framing_source":str(a.framing) if a.framing else "asset_bounds","modes":["textured","clay","wireframe"],"views":["front","back","side","three_quarter"],"textured_mode":"imported materials; texture presence not guaranteed"},indent=2))
    (a.output/"blender_metrics.json").write_text(json.dumps({"before":before,"after":after,"version":bpy.app.version_string},indent=2))
if __name__=="__main__":
    main()
