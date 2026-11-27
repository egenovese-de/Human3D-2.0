# SPDX-License-Identifier: GPL-3.0-or-later
"""Sample both directions against Blender closest-triangle BVHs."""
import json
from pathlib import Path
import sys
import bpy
from mathutils.bvhtree import BVHTree
import numpy as np


def samples(points, faces, seed, count=12000):
    tri = points[faces]
    weights = np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
    rng = np.random.default_rng(seed)
    t = tri[rng.choice(len(tri),count,p=weights/weights.sum())]
    uv = rng.random((count,2))
    uv = np.where(uv.sum(1)[:,None]>1,1-uv,uv)
    return t[:,0]+uv[:,0,None]*(t[:,1]-t[:,0])+uv[:,1,None]*(t[:,2]-t[:,0])


def tree(v,f):
    return BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True)


def distances(v, bvh):
    return np.fromiter((bvh.find_nearest(x)[3] for x in v),float,count=len(v))*10


def stats(d):
    return {name:float(value) for name,value in zip(('mean','median','p95','max'),
                (d.mean(),np.median(d),np.percentile(d,95),d.max()))}


def main(paths, output):
    rows = {}
    for file in paths:
        with np.load(file) as arrays:
            r,f = arrays['reference'],arrays['reference_faces']
            target = tree(r,f)
            from_reference = samples(r,f,819)
            limits = np.linspace(r[f,1].min(),r[f,1].max(),6)
            fits = {}
            for name in arrays.files:
                if name in ('reference','reference_faces','faces'):
                    continue
                v,t = arrays[name],arrays['faces']
                pred = tree(v,t)
                a = samples(v,t,818)
                da,db = distances(a,target),distances(from_reference,pred)
                band = {}
                for i,(lower,upper) in enumerate(zip(limits,limits[1:])):
                    d = np.concatenate([da[(a[:,1]>=lower)&(a[:,1]<upper)],
                                        db[(from_reference[:,1]>=lower)&(from_reference[:,1]<upper)]])
                    if d.size:
                        band[str(i)] = stats(d)
                fits[name] = dict(symmetric_mm=stats(np.r_[da,db]), height_bands_mm=band,
                                  candidate_to_reference_mm=stats(da),reference_to_candidate_mm=stats(db))
                if name in ('E0','E1','E4','E4_full','E9','E10') and file.stem.startswith('A_'):
                    np.save(output.parent/f'{file.stem}-{name}-vertex-residual.npy',distances(v,target))
            rows[file.stem] = fits
            print(file.stem,{k:round(v['symmetric_mm']['mean'],4) for k,v in fits.items()},flush=True)
    output.write_text(json.dumps(rows,indent=2)+'\n')


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    main([Path(path) for path in args[1:]],Path(args[0]))
