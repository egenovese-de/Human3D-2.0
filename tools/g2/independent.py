"""Admit two further historical authored MB-Lab presets for local measurements."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import numpy as np
from g1_benchmark import Engine, triangulate

CASES = {
    'B_female_expanded': ('MBLab_human_female_f_af01_bend0','fd64ed3de8260dccb45e55f518c875553af4567f27ceb9d78c1ac00980f75b9a'),
    'B_male_expanded': ('MBLab_human_male_m_as01_bend0','6b6faf01b4c7ef156d9518bbea774294a40674d7f3d821c5bbc18d196c3ddc19'),
}


def main(historical,output):
    e = Engine()
    faces = triangulate(e.faces)
    native = e.base[e.skin]
    floor,height = native[:,1].min()*10,np.ptp(native[:,1])*10
    for case,(folder,digest) in CASES.items():
        source = historical/folder
        manifest=json.loads((source/'manifest.json').read_text())
        raw=(source/'mesh.json').read_bytes()
        if sha256(raw).hexdigest()!=digest or manifest['mesh_sha256']!=digest:
            raise ValueError('independent reference digest mismatch')
        payload=json.loads(raw)
        xyz=np.asarray(payload['vertices'])
        scale=height/np.ptp(xyz[:,2])
        ref=np.c_[xyz[:,0],xyz[:,2]-xyz[:,2].min(),-xyz[:,1]]*scale
        ref[:,1]+=floor
        np.savez_compressed(output/(case+'.npz'),reference=ref,reference_faces=triangulate(payload['faces']),faces=faces)


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
