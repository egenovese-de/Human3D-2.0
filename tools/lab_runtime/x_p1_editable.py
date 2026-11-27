"""Body-only editable Blender persistence control."""
import bpy, sys, json, hashlib
from pathlib import Path
from mathutils import Quaternion
source,out=map(Path,sys.argv[sys.argv.index("--")+1:])
out.mkdir(parents=True,exist_ok=True)
rows=[]
def digest(obj):
    return hashlib.sha256(repr(([tuple(v.co) for v in obj.data.vertices],[tuple(p.vertices) for p in obj.data.polygons])).encode()).hexdigest()
def positions(obj):
    return [v.co.copy() for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
for path in sorted(source.glob("*.usdz")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assert bpy.ops.wm.usd_import(filepath=str(path.resolve()))=={"FINISHED"}
    body=bpy.context.scene.objects["Body"]
    rig,=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    assert len(rig.data.bones)==163 and len(body.data.vertices)==13380
    assert len(body.data.uv_layers)>0
    assert any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers)
    groups={g.index for g in body.vertex_groups if g.name in rig.data.bones}
    error=max(abs(sum(g.weight for g in v.groups if g.group in groups)-1) for v in body.data.vertices)
    assert error<1e-4
    before=positions(body)
    bone=rig.pose.bones["upperarm01_L"]
    bone.rotation_mode="QUATERNION"
    bone.rotation_quaternion=Quaternion((0,0,1),.15) @ bone.rotation_quaternion
    bpy.context.view_layer.update()
    movement=max((a-b).length for a,b in zip(before,positions(body)))
    assert movement>1e-6
    body.data.vertices[0].co.x+=.01
    body.data.update()
    expected=digest(body)
    uv=[tuple(v.uv) for v in body.data.uv_layers.active.data]
    dest=out/(path.stem+".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(dest.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(dest.resolve()))
    body=bpy.context.scene.objects["Body"]
    assert digest(body)==expected
    assert [tuple(v.uv) for v in body.data.uv_layers.active.data]==uv
    assert any(m.type=="ARMATURE" and m.object and len(m.object.data.bones)==163 for m in body.modifiers)
    rows.append(dict(subject=path.stem,status="PASS",weight_error=error,pose_movement=movement,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
assert len(rows)==4
(out/"editable.json").write_text(json.dumps(rows,indent=2))
print("X_P1_EDITABLE="+json.dumps(rows))
