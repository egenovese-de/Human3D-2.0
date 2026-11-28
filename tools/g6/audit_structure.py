"""Record structural topology provenance and crossing counts for named poses."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from qualify import crossings, tree

p=argparse.ArgumentParser()
for key in ('study','poses','output'):
    p.add_argument(key,type=Path)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
data={'references':{},'poses':{}}
for f in sorted(args.study.glob('*/accepted.npz')):
    with np.load(f) as mesh:
        r,rf=mesh['reference'],mesh['reference_faces']
        rc=crossings(tree(r,rf),rf)
        row=data['references'][f.parent.name]={'reference_crossings':len(rc)}
        if f.parent.name.startswith('A_') and np.array_equal(rf,mesh['faces']):
            v=mesh['R1_extended']
            nc=crossings(tree(v,rf),rf)
            row['retained_r1_crossings_shared_with_reference']=len(nc&rc)
with np.load(args.poses) as mesh:
    faces=mesh['faces']
    rest=crossings(tree(mesh['native'],faces),faces)
    for name in mesh.files:
        if name=='faces':
            continue
        active=crossings(tree(mesh[name],faces),faces)
        data['poses'][name]={'all_crossings':len(active),'new_pairs_vs_native_D0':len(active-rest)}
args.output.write_text(json.dumps(data,indent=2,allow_nan=False))
