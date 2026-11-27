# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender photograph and comparison export using the G2 camera convention."""
from pathlib import Path
import json
import sys
import numpy as np
import bpy

here=Path(__file__).resolve()
sys.path.insert(0,str(here.parents[1]/'g2'))
from blender_evidence import configure, mesh, render
from projection import Camera

keys=('yaw','span','center_y','elevation','distance','perspective','roll','dx','dy')


def main():
    mode,folder,out= sys.argv[sys.argv.index('--')+1:]
    folder,out=Path(folder),Path(out)
    out.mkdir(parents=True,exist_ok=True)
    case=folder.parent/'registration.json'
    payload=json.loads(case.read_text())['views'][folder.name]
    config=payload['truth_camera']
    cam=Camera(**{key:config[key] for key in keys})
    truth=np.load(folder/'truth.npz')
    scene,camera=configure(384)
    reference=mesh('Calibrated observation pose',truth['reference_pose_cm'],truth['faces'],(.53,.32,.22))
    render(scene,camera,cam,out/'reference.png')
    if mode=='fixtures':
        return
    objects=[reference]
    for key,label,col in [('oracle_anchors_perspective','Oracle anchors with estimated camera',(.33,.59,.63)),
                          ('rgb_nominal_shape','RGB registration with nominal anatomy',(.46,.58,.76))]:
        file=folder/(key+'.npz')
        if file.is_file():
            archive=np.load(file)
            obj=mesh(label,archive['posed_cm'],truth['faces'],col)
            objects.append(obj)
            for o in objects:
                o.hide_render=o!=obj
            solution=payload['fits'][key]['estimated_camera']
            estimated=Camera(**{name:solution[name] for name in keys})
            render(scene,camera,estimated,out/(key+'.png'))
    for index,obj in enumerate(objects):
        obj.hide_render=False
        obj.location.x=2*index
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'G3_Registration.blend'))

if __name__=='__main__':
    main()
