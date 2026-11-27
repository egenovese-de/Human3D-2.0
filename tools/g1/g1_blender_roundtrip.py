"""Open, edit and reopen representative admitted USD assets in Blender."""
from pathlib import Path
import json
import sys
import bpy
from mathutils import Vector

def measure():
    body=bpy.data.objects["Body"]
    rig=next(o for o in bpy.context.scene.objects if o.type=="ARMATURE")
    return body,rig

def run(source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assert bpy.ops.wm.usd_import(filepath=str(source.resolve()))=={"FINISHED"}
    body,rig=measure()
    bone=rig.pose.bones["lowerarm01_L"]
    baseline=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points=[v.co.copy() for v in baseline.data.vertices]
    rig.animation_data_clear()
    bone.rotation_mode='QUATERNION'
    bone.rotation_quaternion.rotate(Vector((0,1,0)).rotation_difference(Vector((0,.9,.4))))
    bpy.context.view_layer.update()
    after=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    movement=max((v.co-p).length for v,p in zip(after.data.vertices,points))
    assert movement>1e-4
    p=body.data.vertices[0].co.copy()
    body.data.vertices[0].co.x+=.005
    rendered=source.with_suffix('.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(rendered.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(rendered.resolve()))
    body,rig=measure()
    assert abs((body.data.vertices[0].co-p).length-.005)<1e-5
    return dict(bones=len(rig.data.bones),vertices=len(body.data.vertices),uv_layers=len(body.data.uv_layers),
                articulated_displacement_blender_units=movement,vertex_edit_persisted=True)

if __name__=="__main__":
    folder=Path(sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else sys.argv[1])
    results={p.name:run(p) for p in sorted(folder.glob('*.usdc'))}
    (folder/"blender_roundtrip.json").write_text(json.dumps({"blender":bpy.app.version_string,"results":results},indent=2))
