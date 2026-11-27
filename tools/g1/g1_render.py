"""Standardized Blender orthographic comparison of actual benchmark meshes."""
import argparse
import json
from pathlib import Path
import sys
import math
import bpy
import numpy as np
from mathutils import Vector

def mesh_object(name, xyz, faces, offset, angle):
    # Rotate each column about the same anatomical frame so camera scale is shared.
    c,s=math.cos(angle),math.sin(angle)
    x,y,z=xyz.T
    unique=np.unique(faces)
    remap=np.full(len(xyz),-1,dtype=int)
    remap[unique]=np.arange(len(unique))
    points=np.c_[c*x-s*z+offset,-(s*x+c*z),y][unique]/100
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(points.tolist(),[],remap[faces].tolist())
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    for f in mesh.polygons: f.use_smooth=True
    return obj, unique

def material(name,rgb):
    m=bpy.data.materials.new(name);m.use_nodes=True
    m.node_tree.nodes.get("Principled BSDF").inputs['Base Color'].default_value=(*rgb,1)
    return m

def render(bundle,out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.samples=4
    scene.render.threads_mode="FIXED"
    scene.render.threads=4
    scene.render.resolution_x=1200
    scene.render.resolution_y=420
    scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new("G1 World")
    scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.14,.16,.20,1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value=.5
    camera=bpy.data.objects.new("Camera",bpy.data.cameras.new("Camera"))
    bpy.context.collection.objects.link(camera)
    scene.camera=camera
    camera.location=(0,-8,0)
    camera.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'; camera.data.ortho_scale=6.8
    for name,loc,power,siz in (("key",(-2,-4,4),950,5),("fill",(3,-3,2),650,4)):
        data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.size=siz
        lamp=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(lamp)
        lamp.location=loc; lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
    clay=material("Neutral",(.58,.63,.68))
    heat=material("Unsigned surface residual",(.1,.1,.8))
    nodes=heat.node_tree.nodes
    attr=nodes.new("ShaderNodeVertexColor");attr.layer_name="Residual"
    heat.node_tree.links.new(attr.outputs["Color"],nodes.get("Principled BSDF").inputs["Base Color"])
    rows=[]
    for pose,angle in (("front",0),("side",math.pi/2),("rear",math.pi),("three_quarter",math.pi/4)):
        with np.load(bundle) as a:
            items=[]
            labels=["reference","M1","M4","M5","residual"]
            # Native rest/candidate coordinate differences are preserved; one fixed frame per sheet.
            middle=(a["reference"][:,1].min()+a["reference"][:,1].max())/2
            for i,name in enumerate(labels):
                verts=a["M4" if name=="residual" else name].copy()
                verts[:,1]-=middle
                faces=a["reference_faces" if name=="reference" else "faces"]
                obj,indices=mesh_object(name,verts,faces,(i-2)*125,angle)
                obj.data.materials.append(heat if name=="residual" else clay)
                if name=="residual":
                    color=obj.data.color_attributes.new(name="Residual",type="FLOAT_COLOR",domain="POINT")
                    vals=np.clip(a["residual_mm"][indices]/40,0,1)
                    rgb=np.c_[vals,.35*(1-vals),1-vals,np.ones(len(vals))]
                    color.data.foreach_set("color",rgb.ravel())
                items.append(obj)
                # Lettering stays outside the standardized frame when opened for editing.
        path=out/f"{bundle.stem}_{pose}.png"
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        rows.append(path.name)
        if pose=="front" and bundle.stem.startswith("A_"):
            bpy.ops.wm.save_as_mainfile(filepath=str(out/f"{bundle.stem}.blend"))
            edit=out/f"{bundle.stem}.blend"
            bpy.ops.wm.open_mainfile(filepath=str(edit))
            assert len([o for o in bpy.context.scene.objects if o.type=="MESH"])==5
            scene=bpy.context.scene
            items=[obj for obj in scene.objects if obj.type=="MESH"]
            heat=bpy.data.materials["Unsigned surface residual"]
            clay=bpy.data.materials["Neutral"]
        for obj in items:
            bpy.data.objects.remove(obj,do_unlink=True)
    return rows

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("bundle",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:])
    args.output.mkdir(parents=True,exist_ok=True)
    files=render(args.bundle.resolve(),args.output.resolve())
    (args.output/f"{args.bundle.stem}_render.json").write_text(json.dumps({
        "blender":bpy.app.version_string,"files":files,"columns":["Reference","M1","M4","M5","M4 residual"],
        "heatmap_mm":[0,40],"images":[1200,420],"source":args.bundle.name},indent=2))
