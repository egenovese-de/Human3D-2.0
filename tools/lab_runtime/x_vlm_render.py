"""Render synthetic subject OBJ files or P4 mesh evidence with fixed cameras."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:]
root=Path(args[0]).resolve(); out=Path(args[1]).resolve();out.mkdir(parents=True,exist_ok=True)
data = json.loads(root.read_text()) if root.is_file() else None
names = sorted(data["vertices"]) if data else [p.stem for p in sorted(root.glob("*.obj"))]
report=[]
for name in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if data:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(x, -z, y) for x, y, z in data["vertices"][name]], [], data["triangles"])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
    else:
        bpy.ops.wm.obj_import(filepath=str(root/(name+".obj")),forward_axis='NEGATIVE_Z',up_axis='Y')
        obj=next(o for o in bpy.context.scene.objects if o.type=="MESH")
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=4
    scene.cycles.use_denoising=False
    scene.world=bpy.data.worlds.new("Studio")
    scene.world.use_nodes=True
    scene.world.node_tree.nodes.get("Background").inputs[0].default_value=(.25,.25,.25,1)
    scene.world.node_tree.nodes.get("Background").inputs[1].default_value=.6
    mat=bpy.data.materials.new("Clay");mat.diffuse_color=(.72,.72,.72,1)
    obj.data.materials.clear();obj.data.materials.append(mat)
    for pos,power in [((10,-15,18),2500),((-12,-8,8),1800),((0,12,15),2200)]:
        bpy.ops.object.light_add(type='AREA',location=pos)
        lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=12
        lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=576;scene.render.resolution_y=576;scene.render.resolution_percentage=100; scene.render.threads_mode="FIXED"; scene.render.threads=4
    scene.render.image_settings.file_format='PNG'
    # Common world frame in MakeHuman decimetres, not per-mesh auto framing.
    center=Vector((0,0,0))
    bpy.ops.object.camera_add()
    cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=24;scene.camera=cam
    views = [("front",(0,-40,0)),("side",(40,0,0)),("threequarter",(28,-28,0))]
    if data:
        views.pop(1)
    for label,pos in views:
        cam.location=Vector(pos);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        p=out/(name+"_"+label+".png");scene.render.filepath=str(p);bpy.ops.render.render(write_still=True)
        report.append({"mesh":name,"view":label,"file":p.name,"vertices":len(obj.data.vertices),"polygons":len(obj.data.polygons)})
(out/"render_report.json").write_text(json.dumps(report,indent=2))
