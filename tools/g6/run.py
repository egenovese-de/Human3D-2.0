"""Reproduce G5 D9 and run the isolated G6 geometry capacity matrix."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import resource
from time import perf_counter

import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import eye
from scipy.spatial import cKDTree

from deformation import adjacency, cage, ffd, fit, graph, laplacian, samples, unit_normals
from human3d.experimental import NativeBasis
from human3d.frozen_body import load_project_body
from human3d.native_rig import validate_rebind
from human3d.session import Session
from refinement import direct_fit

EXTRAS = ['torso/torso-scale-vert', 'torso/torso-vshape', 'stomach/stomach-tone',
          'hip/hip-scale-depth', 'pelvis/pelvis-tone', 'breast/breast-point',
          'measure/measure-shoulder-dist', 'measure/measure-calf-circ',
          'neck/neck-scale-vert', 'head/head-scale-horiz', 'armslegs/l-upperarm-scale-horiz',
          'armslegs/r-upperarm-scale-horiz']


def optimize(model, initial, bounds, start, faces, reference, rf, same, epochs, budget, state):
    rng = np.random.default_rng(47)
    active = np.unique(faces)
    fit_ids = np.sort(rng.choice(active, min(1700, len(active)), replace=False))
    target = samples(reference, rf, 9000, 153)
    probes = target[::5]
    lookup = cKDTree(target)
    counter = 0
    curve = []
    for _ in range(epochs):
        points = model(start)
        _, matched = lookup.query(points[fit_ids])
        _, reverse = cKDTree(points[active]).query(probes)
        ref = reference[fit_ids] if same else target[matched]

        def residual(x):
            nonlocal counter
            counter += 1
            p = model(x)
            forward = (p[fit_ids] - ref).ravel()
            back = np.empty(0) if same else (.8*(p[active[reverse]] - probes)).ravel()
            return np.r_[forward, back, .15*(x-initial)]

        result = least_squares(residual, start, bounds=bounds, max_nfev=budget, loss='soft_l1',
                               f_scale=1.2, diff_step=1e-3)
        start = result.x
        curve.append({'evaluations': counter, 'optimizer_cost': float(result.cost),
                      'optimality': float(result.optimality), 'termination_status': result.status,
                      'target_sample_mean_mm': float(lookup.query(model(start)[fit_ids])[0].mean()*10)})
    state.update(curve=curve, evaluations=counter, parameters=start.tolist())
    return model(start)


def det_matrix(a):
    return np.linalg.det(np.stack((a[:,1]-a[:,0], a[:,2]-a[:,0], a[:,3]-a[:,0]), axis=-1))


def benchmark(args):
    with np.load(args.reference, allow_pickle=False) as data:
        reference, ref_faces, faces = (data[x].copy() for x in ('reference','reference_faces','faces'))
    session = Session(args.baseline / 'project')
    body = load_project_body(session.store)
    controls = NativeBasis(args.runtime, body)
    seed = np.load(args.baseline/'D0.npy')
    manifest = json.loads((args.baseline/'attempt.json').read_text())
    cache, = (args.baseline/'project'/'experimental-canonical').glob('*.npz')
    with np.load(cache) as record:
        parameters, _, _ = json.loads(str(record['metadata']))
    case = args.reference.stem
    same = case.startswith('A_')
    folder = args.output/case
    folder.mkdir(parents=True, exist_ok=True)
    rows, meshes = {}, {'D0': seed * 10, 'initial': controls.evaluate(controls.initial)*10}

    def record(name, operation, parent='D0'):
        began = perf_counter()
        row = rows[name] = {'parent':parent}
        proposed = operation(row)
        previous = meshes[parent]
        row['max_displacement_mm'] = float(np.linalg.norm(proposed-previous,axis=1).max()*10)
        a = previous[faces]
        normal = np.cross(a[:,1]-a[:,0], a[:,2]-a[:,0])
        span = np.linalg.norm(normal,axis=1)
        for alpha in (1., .75, .5, .25, .125, .0625, 0.):
            candidate = previous + alpha * (proposed-previous)
            try:
                validate_rebind(body, candidate / 10)
                if not np.isfinite(candidate).all():
                    raise ValueError('non-finite candidate')
                t = candidate[faces]
                n = np.cross(t[:,1]-t[:,0], t[:,2]-t[:,0])
                if np.any((normal*n).sum(1)[span>1e-4] <= 0):
                    raise ValueError('face flip relative to parent')
                break
            except ValueError as error:
                row.setdefault('pre_bvh_rejections', []).append(str(error))
        meshes[name] = candidate
        row.update(seconds=perf_counter()-began, accepted_fraction_pre_bvh=alpha,
                   geometry_sha256=sha256(candidate.astype('<f8').tobytes()).hexdigest())
        print(case, name, round(row['seconds'],2), alpha, flush=True)

    def g5(row):
        v, d = direct_fit(controls, body, faces, reference, ref_faces, parameters, same)
        row.update(d)
        return v*10
    record('R0_D9', g5)
    base_names = [*controls.globals,*controls.regional]
    low = [(.49 if n=='Age' else .10) if n in controls.globals else -.65 for n in base_names]
    high = [.90 if n in controls.globals else .65 for n in base_names]
    x = np.clip(np.array([parameters[n] for n in base_names]), low, high)
    predict = lambda z: controls.evaluate(dict(zip(base_names,z)))*10
    record('R0_long', lambda row: optimize(predict,x,(low,high),x,faces,reference,ref_faces,same,9,9,row))
    midpoint = (np.array(low)+np.array(high))/2
    record('R0_restart', lambda row: optimize(predict,x,(low,high),midpoint,faces,reference,ref_faces,same,9,9,row))

    if not args.skip_native_extension:
        from g1_benchmark import Engine
        e = Engine()
        last = np.array(rows['R0_long']['parameters'])
        native_base_names = [e.mac.get(k,k) for k in base_names]
        if not all(k in e.mods for k in native_base_names):
            raise ValueError('Product control missing from native registry')
        extras = [k for stem in EXTRAS for k in e.mods
                  if k.startswith(stem+'-') and k.endswith('decr|incr') and e.defs[k]]
        names = native_base_names + extras
        bounds = low + [max(-.65,e.mods[k][0].getMin()) for k in extras], high + [.65]*len(extras)
        start = np.clip(np.r_[last, np.full(len(extras), .003)], *bounds)
        def native(row):
            row['names'] = names
            return optimize(lambda z:e.extended(dict(zip(names,z)))*10, start, bounds, start, faces,
                            reference, ref_faces, same, 8, 8, row)
        record('R1_extended', native)
    source = meshes['R0_long']
    edges = adjacency(source,faces)
    active = np.unique(faces)
    def deform(row, basis, smooth, steps, weight, mode, anchor=source):
        p, curve = fit(anchor,faces,reference,ref_faces,basis,smooth,
                       steps=steps,weight=weight,mode=mode,same=same)
        row.update(curve=curve, controls=basis.shape[1], mode=mode, budget=steps)
        return p
    preferred = 'known' if same else 'symmetric'
    for suffix, dims in [('coarse',(3,5,3)),('fine',(5,8,5))]:
        b,l = ffd(source,dims)
        record(f'R2_{suffix}',lambda row:deform(row,b,l,14,4.,preferred),'R0_long')
        if suffix == 'fine':
            record('R2_fine_budget6',lambda row:deform(row,b,l,6,4.,preferred),'R0_long')
            record('R2_fine_long',lambda row:deform(row,b,l,28,4.,preferred),'R0_long')
    b,l,lattice = cage(source)
    def cage_fit(row):
        result = deform(row,b,l,14,4.,preferred)
        # Recover control offsets for a piecewise affine Jacobian diagnostic.
        from scipy.sparse.linalg import lsqr
        nodes = np.stack([lsqr(b,result[:,j]-source[:,j],iter_lim=380)[0] for j in range(3)],axis=1)
        original = det_matrix(lattice.points[lattice.simplices])
        later = det_matrix((lattice.points+nodes)[lattice.simplices])
        ratios = later[np.abs(original)>1e-6]/original[np.abs(original)>1e-6]
        row['approx_candidate_cage_det_min'] = float(ratios.min())
        row['approx_candidate_cage_det_nonpositive'] = int((ratios<=0).sum())
        return result
    record('R3_cage',cage_fit,'R0_long')
    for count in (48,120):
        b,l = graph(source,edges,active,count)
        record(f'R4_graph{count}',lambda row:deform(row,b,l,14,4.,preferred),'R0_long')
    identity = eye(len(source),format='csr')
    smooth = laplacian(edges)
    for mode in (('known','nearest','symmetric') if same else ('nearest','regions','normals','symmetric')):
        record(f'R5_{mode}',lambda row:deform(row,identity,smooth,14,9.,mode),'R0_long')
    record('R5_symmetric_budget6',lambda row:deform(row,identity,smooth,6,9.,'symmetric'),'R0_long')
    record('R5_symmetric_long',lambda row:deform(row,identity,smooth,28,9.,'symmetric'),'R0_long')
    for tag, parent in [('lattice','R2_fine'),('graph','R4_graph120')]:
        source_stage=meshes[parent]
        s=laplacian(adjacency(source_stage,faces))
        record('R6_'+tag,lambda row:deform(row,identity,s,12,14.,preferred,source_stage),parent)
    np.savez_compressed(folder/'proposals.npz',reference=reference,reference_faces=ref_faces,faces=faces,**meshes)
    report={'source_m7':manifest.get('engine','geometry'),'baseline_runtime':manifest,
            'study':rows,'peak_rss_kib_process':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    (folder/'fit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('runtime','reference','baseline','output'):
        parser.add_argument(key,type=Path)
    parser.add_argument('--skip-native-extension',action='store_true')
    benchmark(parser.parse_args())
