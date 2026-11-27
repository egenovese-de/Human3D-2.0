"""Render actual P1 OBJ geometry, fixed orthographic cameras, no generative imagery."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:]
root=Path(args[0]).resolve(); out=Path(args[1]).resolve();out.mkdir(parents=True,exist_ok=True)
names=["hold01_expanded_truth","hold01_macro_only_expanded","hold01_weight_muscle_expanded","hold01_expanded_expanded","hold02_expanded_truth","hold02_macro_only_expanded","hold02_weight_muscle_expanded","hold02_expanded_expanded"]
report=[]
for name in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(root/(name+".obj")),forward_axis='NEGATIVE_Z',up_axis='Y')
    obj=next(o for o in bpy.context.scene.objects if o.type=="MESH")
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO'
    scene.display.shading.color_type='SINGLE'
    scene.display.shading.single_color=(.72,.72,.72)
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    # Common world frame in MakeHuman decimetres, not per-mesh auto framing.
    center=Vector((0,0,0))
    bpy.ops.object.camera_add()
    cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=24;scene.camera=cam
    for label,pos in [("front",(0,-40,0)),("side",(40,0,0)),("threequarter",(28,-28,0))]:
        cam.location=Vector(pos);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        p=out/(name+"_"+label+".png");scene.render.filepath=str(p);bpy.ops.render.render(write_still=True)
        report.append({"mesh":name,"view":label,"file":p.name,"vertices":len(obj.data.vertices),"polygons":len(obj.data.polygons)})
(out/"render_report.json").write_text(json.dumps(report,indent=2))
