"""Controlled rig and posture probes on accepted G6 canonical assets."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.spatial.transform import Rotation

from human3d.frozen_body import load_project_body
from human3d.native_rig import _swing, skin_vertices, validate_pose, validate_rebind
from human3d.session import Session


def art(rig, joints, relative, directions=None):
    transforms={}
    directions=directions or {}
    def visit(name):
        if name in transforms:
            return transforms[name]
        bone=rig['bones'][name]
        parent=bone['parent']
        r,t=visit(parent) if parent else (np.eye(3),np.zeros(3))
        where=r@joints[bone['head']]+t
        turn=relative.get(name,np.eye(3))
        if name in directions:
            turn = _swing(r @ (joints[bone['tail']]-joints[bone['head']]),directions[name])
        transforms[name]=(turn@r,where+turn@(t-where))
        return transforms[name]
    for name in rig['bones']:
        visit(name)
    return transforms


def settings(rig):
    bones=rig['bones']
    def axis(vector,degree):
        return Rotation.from_rotvec(np.asarray(vector)*np.deg2rad(degree)).as_matrix()
    torso=next((n for n in ('spine01','spine02','spine03') if n in bones),None)
    return {'neutral':{}, 'arm_elevation':{f'upperarm01.{side}':axis([0,0,1],d)
          for side,d in [('L',35),('R',-35)]},
          'elbow':{'lowerarm01.L':axis([0,1,0],-42)},
          'hip':{'upperleg01.L':axis([1,0,0],-28)},
          'knee':{'lowerleg01.R':axis([1,0,0],42)},
          'torso':{torso:axis([0,1,0],20)} if torso else {},
          'asymmetric':{'upperarm01.L': axis([0,0,1],30),'lowerleg01.R':axis([1,0,0],28)}}


def common_pose(kind):
    if kind=='native':
        return {}
    tilt={'A':-30,'T':0,'X':30}[kind]
    dirs={}
    for side,sign in [('L',1),('R',-1)]:
        direction=np.array([sign*np.cos(np.deg2rad(tilt)),np.sin(np.deg2rad(tilt)),0])
        for segment in ('upperarm','lowerarm'):
            dirs[f'{segment}01.{side}']=direction
        if kind=='X':
            dirs[f'upperleg01.{side}']=np.array([sign*.28,-1,0])
    return dirs


def main(args):
    report={}
    for folder in sorted(args.study.iterdir()):
        if not (folder/'accepted.npz').exists():
            continue
        body=load_project_body(Session(args.baseline/folder.name/'calibrated'/'project').store)
        rig=body['rig']
        geometry={}
        with np.load(folder/'accepted.npz') as data:
            faces=data['faces']
            ref=data['reference']
            original=data['D0']/10
            origin_joints=validate_rebind(body,original)
            row=report[folder.name]={}
            names=['D0','R0_long','R1_extended','R2_fine','R4_graph120','R5_symmetric','R6_graph']
            for name in names:
                if name not in data:
                    continue
                start=perf_counter()
                mesh=data[name]/10
                digest=sha256(mesh.astype('<f8').tobytes()).hexdigest()
                arm=row[name]={'canonical_sha256':digest}
                try:
                    rebound=validate_rebind(body,mesh)
                except ValueError as e:
                    arm['rejected']=str(e)
                    continue
                if folder.name.startswith('A_'):
                    try:
                        exact={key:np.asarray(ref/10)[idx].mean(0) for key,idx in rig['joint_vertices'].items()}
                        error=lambda joints: np.mean([np.linalg.norm(joints[k]-exact[k])*100 for k in exact])
                        arm['joint_center_rebound_mean_mm']=float(error(rebound))
                        arm['joint_center_retained_mean_mm']=float(error(origin_joints))
                    except IndexError:
                        exact=None
                else:
                    exact=None
                lengths=lambda joints:np.array([np.linalg.norm(joints[b['head']]-joints[b['tail']])
                                               for b in rig['bones'].values()])
                arm['mean_absolute_bone_change_vs_D0_mm']=float(np.abs(lengths(rebound)-lengths(origin_joints)).mean()*100)
                arm['poses']={}
                for label, rotations in settings(rig).items():
                    modes={}
                    for bind,joints in [('retained',origin_joints),('rebound',rebound)]:
                        moved=skin_vertices(mesh,rig['skin'],art(rig,joints,rotations))
                        try:
                            validate_pose(body,mesh,moved)
                            valid=True
                        except ValueError:
                            valid=False
                        t, m=mesh[faces],moved[faces]
                        lens=np.linalg.norm(t[:,1]-t[:,0],axis=1)
                        ratio=np.linalg.norm(m[:,1]-m[:,0],axis=1)[lens>1e-7]/lens[lens>1e-7]
                        modes[bind]={'valid':valid,'edge_ratio_p95':float(np.percentile(ratio,95))}
                        if exact:
                            ref_pose=skin_vertices(ref/10,rig['skin'],art(rig,exact,rotations))
                            modes[bind]['same_topology_mean_mm']=float(np.linalg.norm(
                               moved[np.unique(faces)]-ref_pose[np.unique(faces)],axis=1).mean()*100)
                        if bind=='rebound' and folder.name=='A_heldout_1' and name in ('D0','R2_fine','R6_graph'):
                            geometry[f'{name}_{label}']=moved*10
                    arm['poses'][label]=modes
                    assert sha256(mesh.astype('<f8').tobytes()).hexdigest()==digest
                arm['seconds']=perf_counter()-start
            if geometry:
                for kind in ('native','A','T','X'):
                    geometry[kind]=skin_vertices(original,rig['skin'],art(rig,origin_joints,{},common_pose(kind)))*10
                np.savez_compressed(args.output.parent/'poses.npz',faces=faces,**geometry)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('study','baseline','output'):
        parser.add_argument(name,type=Path)
    main(parser.parse_args())
