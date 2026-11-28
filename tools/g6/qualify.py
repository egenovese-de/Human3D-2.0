"""G6 exact closest-triangle scores and parent-relative crossing qualification."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from mathutils.bvhtree import BVHTree


def tree(vertices, faces):
    return BVHTree.FromPolygons(vertices.tolist(),faces.tolist(),all_triangles=True)


def crossings(bvh, faces):
    pairs = np.asarray(bvh.overlap(bvh),dtype=np.int32).reshape(-1,2)
    a,b = pairs[pairs[:,0]<pairs[:,1]].T
    disjoint = ~(faces[a,:,None] == faces[b,None,:]).any(axis=(1,2))
    return set(zip(a[disjoint].tolist(), b[disjoint].tolist()))


def stats(values):
    return {key:float(value) for key,value in zip(('mean','median','rms','p95','max'),
            (values.mean(),np.median(values),np.sqrt(np.mean(values**2)),np.percentile(values,95),values.max()))}


def score(points, ref, faces, ref_faces, surface, sample):
    ref_bvh, ref_pts = ref
    bvh = tree(points,faces)
    pts = sample(points,faces,818)
    distance = lambda values, mesh: np.fromiter((mesh.find_nearest(x)[3] for x in values),float,count=len(values))*10
    a,b = distance(pts,ref_bvh),distance(ref_pts,bvh)
    result = stats(np.r_[a,b])
    result['coverage_10mm_forward'] = float((a<=10).mean())
    result['coverage_10mm_reverse'] = float((b<=10).mean())
    height = np.linspace(ref_pts[:,1].min(),ref_pts[:,1].max(),7)
    result['height_band_mean_mm'] = [float(np.r_[a[(pts[:,1]>=low)&(pts[:,1]<high)],
                                                      b[(ref_pts[:,1]>=low)&(ref_pts[:,1]<high)]].mean())
                                    for low,high in zip(height[:-1],height[1:])]
    return result


def main(args, sample):
    res = {}
    for file in sorted(args.study.glob('*/proposals.npz')):
        if args.case and file.parent.name != args.case:
            continue
        with np.load(file) as data:
            faces=data['faces']; ref_faces=data['reference_faces']; geometry=data['reference']
            ref=(tree(geometry,ref_faces),sample(geometry,ref_faces,819))
            report=json.loads((file.parent/'fit.json').read_text())
            approved={'faces':faces,'reference_faces':ref_faces,'reference':geometry}
            bases={key:(data[key],crossings(tree(data[key],faces),faces))
                   for key in ('D0','B_estimated') if key in data.files}
            out = {}
            for name in data.files:
                if name in approved:
                    continue
                start=perf_counter()
                proposed=data[name]
                parent='B_estimated' if name.startswith('P_estimated') else 'D0'
                base,parent_cross=bases[parent]
                a=base[faces]; qa=proposed[faces]
                norm=lambda t: np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
                n0,n1=norm(a),norm(qa)
                den=np.linalg.norm(n0,axis=1)
                ratios=np.linalg.norm(n1,axis=1)[den>1e-7]/den[den>1e-7]
                edge=np.linalg.norm(qa[:,1]-qa[:,0],axis=1)/np.maximum(1e-8,np.linalg.norm(a[:,1]-a[:,0],axis=1))
                flips=int(((n0*n1).sum(1)[den>1e-4] <= 0).sum())
                before=crossings(tree(proposed,faces),faces)
                proposal=score(proposed,ref,faces,ref_faces,None,sample)
                alpha=1.
                # R0 and initial serve as measured historical controls. Record defects
                # without changing their published geometry.
                take=proposed
                if name.startswith(('R1','R2','R3','R4','R5','R6','P_')):
                    if before-parent_cross or flips:
                        for alpha in (.75,.5,.25,.125,.0625,0.):
                            trial=base+alpha*(proposed-base)
                            nn=norm(trial[faces])
                            if np.any((n0*nn).sum(1)[den>1e-4]<=0):
                                continue
                            if not crossings(tree(trial,faces),faces)-parent_cross:
                                take=trial
                                break
                approved[name]=take
                out[name]={'proposal':proposal,
                           'accepted':proposal if alpha==1 else score(take,ref,faces,ref_faces,None,sample),
                           'fraction_vs_parent':alpha,'structural_parent':parent,'new_crossings_proposal':len(before-parent_cross),
                           'all_crossings_proposal':len(before),'face_flips_vs_D0_proposal':flips,
                           'proposal_area_ratio_minmax':[float(ratios.min()),float(ratios.max())],
                           'proposal_edge_ratio_p95':float(np.percentile(edge,95)),
                           'accepted_vertex_sha256':sha256(take.astype('<f8').tobytes()).hexdigest(),
                           'qualification_s':perf_counter()-start}
            print(file.parent.name,{n:round(x['accepted']['mean'],3) for n,x in out.items()},flush=True)
            res[file.parent.name]=out
            np.savez_compressed(file.parent/'accepted.npz',**approved)
            (file.parent/'surface.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    args.output.write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('g4','study','output'):
        parser.add_argument(key,type=Path)
    parser.add_argument('--case')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    sys.path.insert(0,str(args.g4.resolve()/'tools/g2'))
    from surface import samples
    main(args,samples)
