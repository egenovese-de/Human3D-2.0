"""One-level midpoint subdivision control with fixed surface, measured in Blender."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from mathutils.bvhtree import BVHTree

parser=argparse.ArgumentParser(description=__doc__)
for key in ('source','output'):
    parser.add_argument(key,type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
started=perf_counter()
with np.load(args.source) as d:
    f,v = d['faces'],d['D0']
    r,rf=d['reference'],d['reference_faces']
unique, inv = np.unique(np.sort(f[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0,return_inverse=True)
a,b,c=f.T
ab,bc,ca=(inv.reshape(-1,3)+len(v)).T
tri=np.vstack((np.c_[a,ab,ca],np.c_[ab,b,bc],np.c_[ca,bc,c],np.c_[ab,bc,ca]))
points=np.vstack((v,v[unique].mean(axis=1)))
tree=lambda p,pf:BVHTree.FromPolygons(p.tolist(),pf.tolist(),all_triangles=True)
base=tree(v,f); ref=tree(r,rf); fine=tree(points,tri)
new=points[len(v):]
midpoint_error=np.array([base.find_nearest(x)[3]*10 for x in new])
reference=np.unique(rf)
ids=np.random.default_rng(6).choice(reference, min(6000,len(reference)),replace=False)
old_d=np.array([base.find_nearest(x)[3] for x in r[ids]])*10
new_d=np.array([fine.find_nearest(x)[3] for x in r[ids]])*10
summary={'old_vertices':len(v),'new_vertices':len(points),'old_triangles':len(f),'new_triangles':len(tri),
         'mesh_array_bytes_before':v.nbytes+f.nbytes,'mesh_array_bytes_after':points.nbytes+tri.nbytes,
         'midpoint_max_distance_original_mm':float(midpoint_error.max()),
         'max_change_reference_distance_mm':float(np.abs(old_d-new_d).max()),
         'seconds':perf_counter()-started,
         'qualification':'Geometric identity under linear subdivision. No detail fit or UV/skin export in this experiment.'}
args.output.write_text(json.dumps(summary,indent=2))
