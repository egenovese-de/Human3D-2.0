# SPDX-License-Identifier: GPL-3.0-or-later
"""Render separate armature-bound layers from a directly imported USDZ."""
import argparse
from pathlib import Path

import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont


def run(source, work, atlas, *, native=False):
    work.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if bpy.ops.wm.usd_import(filepath=str(source.resolve()))!={"FINISHED"}:
        raise RuntimeError("direct USDZ import failed")
    scene=bpy.context.scene
    body=scene.objects["Body"]
    inner=scene.objects["top_base" if native else "independent_base"]
    outer=scene.objects["top_outer" if native else "independent_outer"]
    rig=next(o for o in scene.objects if o.type=="ARMATURE")
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=scene.render.resolution_y=380
    scene.render.resolution_percentage=100
    scene.display.shading.color_type="OBJECT"
    scene.display.shading.light="STUDIO"
    scene.display.shading.show_shadows=False
    body.color=(.44,.29,.20,1)
    inner.color=(.11,.34,.65,1)
    outer.color=(.63,.26,.15,1)
    camera=bpy.data.objects.new("Inspection",bpy.data.cameras.new("Inspection"))
    scene.collection.objects.link(camera)
    scene.camera=camera
    camera.data.type="ORTHO"
    corners=[body.matrix_world@Vector(p) for p in body.bound_box]
    center=sum(corners,Vector())/8
    span=max(p.z for p in corners)-min(p.z for p in corners)
    camera.data.ortho_scale=span*1.13
    camera.location=center+Vector((.8*span,-2.1*span,.15*span))
    camera.rotation_euler=(center-camera.location).to_track_quat("-Z","Y").to_euler()
    cases=(("Imported pose",False,False,False),("Outer layer hidden",False,True,False),
           ("Garments hidden",True,True,False),("Armature edited",False,False,True))
    for index,(_,hide_inner,hide_outer,edit) in enumerate(cases):
        inner.hide_render=hide_inner
        outer.hide_render=hide_outer
        if edit:
            pose = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
            rig.animation_data_clear()
            for bone in rig.pose.bones:
                bone.matrix_basis = pose[bone.name]
            rig.pose.bones["upperarm01_L"].rotation_quaternion.rotate(
                Vector((0,1,0)).rotation_difference(Vector((.8,.45,.4))))
        scene.render.filepath=str((work/f"{index}.png").resolve())
        bpy.ops.render.render(write_still=True)
    img=Image.new("RGB",(1220,400),"#eeeef3")
    draw=ImageDraw.Draw(img)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",18)
    bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",24)
    title = "Human3D M6 · direct USDZ import" if native else "Direct USDZ import · independent registered garment control"
    draw.text((25,14),title,fill="#181b2b",font=bold)
    for i,(label,*_) in enumerate(cases):
        p=Image.open(work/f"{i}.png").convert("RGB").resize((286,286),Image.Resampling.LANCZOS)
        x=25+i*300
        img.paste(p,(x,54))
        draw.text((x,350),label,fill="#181b2b",font=font)
    img.save(atlas,optimize=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("source","work","atlas"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--native", action="store_true")
    run(**vars(parser.parse_args()))
