"""Compute sampled point-to-triangle distances against Blender BVHs."""
from pathlib import Path
import sys
import json
import numpy as np
import bpy  # Initializes Blender's bundled mathutils module.
from mathutils.bvhtree import BVHTree
from g1_benchmark import sample, summary, dump

def tree(v,t):
    return BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True)

def distance(query,bvh):
    return np.fromiter((bvh.find_nearest(p)[3] for p in query),float,count=len(query))*10

def main(root):
    results=[]
    for p in sorted(root.glob("*.npz")):
        with np.load(p) as a:
            ref=a["reference"]; rt=a["reference_faces"]; faces=a["faces"]
            oracle=tree(ref,rt)
            truth=sample(ref,rt,12000,819)
            bounds=ref[np.unique(rt),1]
            planes=np.linspace(bounds.min(),bounds.max(),6)
            rows={}
            for key in ("M0","M1","M2","M3","M4","M5"):
                points=a[key]
                pred=tree(points,faces)
                query=sample(points,faces,12000,818)
                forward=distance(query,oracle)
                backward=distance(truth,pred)
                bands={}
                for i,(lo,hi) in enumerate(zip(planes,planes[1:])):
                    q=(query[:,1]>=lo)&(query[:,1]<hi)
                    r=(truth[:,1]>=lo)&(truth[:,1]<hi)
                    bands[str(i)]=summary(np.r_[forward[q],backward[r]])
                rows[key]={"symmetric_mm":summary(np.r_[forward,backward]),"candidate_to_reference_mm":summary(forward),
                           "reference_to_candidate_mm":summary(backward),"height_bands_mm":bands}
            print(p.stem,[round(rows[k]["symmetric_mm"]["mean"],5) for k in rows],flush=True)
            results.append({"case":p.stem,"rows":rows})
    dump(root/"exact_surface.json",results)
if __name__=="__main__":
    main(Path(sys.argv[1]))
