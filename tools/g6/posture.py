"""Frozen MB-Lab skeletal-direction controls and product skinning."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from human3d.frozen_body import load_project_body
from human3d.native_rig import skin_vertices, validate_rebind, validate_pose
from human3d.session import Session
from pose import art


def main(args):
    data=json.loads(args.manifest.read_text())['families']['B']['cases']
    bones={'upperarm':'upperarm01','lowerarm':'lowerarm01','thigh':'upperleg01',
           'calf':'lowerleg01','hand':'wrist','foot':'foot'}
    log={}
    for row in data:
        case,preset=row['id'],row['preset']
        sex='female' if preset.startswith('f') else 'male'
        source=args.historical/f'MBLab_human_{sex}_{preset}_bend0'
        if sha256((source/'mesh.json').read_bytes()).hexdigest()!=row['source_mesh_sha256']:
            raise ValueError(f'Source identity mismatch {case}')
        raw=json.loads((source/'mesh.json').read_text())
        target=json.loads((source/'manifest.json').read_text())['joint_anchors']
        body=load_project_body(Session(args.baseline/case/'calibrated'/'project').store)
        rig=body['rig']
        with np.load(args.study/case/'accepted.npz') as item:
            vertices,faces,ref,rf=[item[name] for name in ('R0_D9','faces','reference','reference_faces')]
        p=np.asarray(raw['vertices'])
        scale=np.ptp(ref[np.unique(rf),1])/np.ptp(p[:,2])
        offsets=[0,ref[np.unique(rf),1].min()-p[:,2].min()*scale,0]
        anchors={bones[name.rsplit('_',1)[0]]+'.'+name.rsplit('_',1)[1]:
                 np.asarray(points)[:,[0,2,1]]*[scale,scale,-scale]+offsets for name,points in target.items()}
        neutral=vertices/10
        joints=validate_rebind(body,neutral)
        diagnostics={}
        poses={'D0':vertices}
        for variant,keys in [('Posture_arm',[k for k in anchors if 'arm' in k]),
                             ('Posture_limbs',list(anchors))]:
            directions={k:points[1]-points[0] for k in keys for points in (anchors[k],)}
            tr=art(rig,joints,{},directions)
            moved=skin_vertices(neutral,rig['skin'],tr)
            validate_pose(body,neutral,moved)
            error=[]
            for key in keys:
                bone=rig['bones'][key]
                r,t=tr[key]
                pred=np.array([r@joints[bone[k]]+t for k in ('head','tail')])*10
                error.extend((np.linalg.norm(pred-anchors[key],axis=1)*10).tolist())
            diagnostics[variant]={'target_bones':keys,'joint_endpoint_mean_mm':float(np.mean(error))}
            poses[variant]=moved*10
        folder=args.output/case
        folder.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(folder/'proposals.npz',reference=ref,reference_faces=rf,faces=faces,**poses)
        (folder/'fit.json').write_text(json.dumps({'study':diagnostics}))
        log[case]=diagnostics
    (args.output/'landmarks.json').write_text(json.dumps(log,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','historical','baseline','study','output'):
        parser.add_argument(name,type=Path)
    main(parser.parse_args())
