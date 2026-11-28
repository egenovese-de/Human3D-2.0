"""Sparse direct-geometry deformation controls, all coordinates in centimetres."""
import numpy as np
from scipy.interpolate import BSpline
from scipy.sparse import coo_matrix, csr_matrix, diags, eye, kron, vstack
from scipy.sparse.csgraph import dijkstra
from scipy.sparse.linalg import factorized
from scipy.spatial import Delaunay, cKDTree


def adjacency(vertices, faces):
    pairs = np.unique(np.sort(np.vstack((faces[:, :2], faces[:, 1:], faces[:, ::2])), axis=1), axis=0)
    a, b = pairs.T
    lengths = np.linalg.norm(vertices[a] - vertices[b], axis=1)
    return csr_matrix((np.r_[lengths, lengths], (np.r_[a, b], np.r_[b, a])), shape=(len(vertices), len(vertices)))


def laplacian(edges):
    unit = edges.copy()
    unit.data[:] = 1
    return diags((np.asarray(unit.sum(axis=1)).ravel() > 0).astype(float)) - diags(
        1 / np.maximum(np.asarray(unit.sum(axis=1)).ravel(), 1)) @ unit


def grid_regularizer(dims):
    n = np.prod(dims)
    index = np.arange(n).reshape(dims)
    pairs = []
    for axis in range(3):
        left = np.swapaxes(index, axis, 0)
        pairs.append(np.column_stack((left[:-1].ravel(), left[1:].ravel())))
    a, b = np.vstack(pairs).T
    i = np.arange(len(a))
    return csr_matrix((np.r_[np.ones(len(a)), -np.ones(len(a))], (np.r_[i, i], np.r_[a, b])),
                      shape=(len(a), n))


def ffd(vertices, dims):
    lo, hi = vertices.min(0), vertices.max(0)
    x = np.clip((vertices - lo) / (hi - lo), 0, 1)
    axes = []
    for axis, count in enumerate(dims):
        degree = min(3, count - 1)
        knots = np.r_[np.zeros(degree), np.linspace(0, 1, count - degree + 1), np.ones(degree)]
        axes.append(BSpline.design_matrix(x[:, axis], knots, degree).toarray())
    basis = csr_matrix(np.einsum('ni,nj,nk->nijk', *axes).reshape(len(x), -1))
    return basis, grid_regularizer(dims)


def cage(vertices):
    """Piecewise-affine tetrahedral boundary cage with harmonic graph smoothing."""
    lo, hi = vertices.min(0), vertices.max(0)
    extent = hi - lo
    grid = np.array(np.meshgrid(np.linspace(-.08, 1.08, 4), np.linspace(-.08, 1.08, 7),
                                np.linspace(-.08, 1.08, 4), indexing='ij')).reshape(3, -1).T
    boundary = np.any((grid < 0) | (grid > 1), axis=1)
    controls = lo + grid[boundary] * extent
    lattice = Delaunay(controls)
    simplex = lattice.find_simplex(vertices)
    if np.any(simplex < 0):
        raise ValueError('Vertex outside cage')
    t = lattice.transform[simplex]
    a = np.einsum('nij,nj->ni', t[:, :3], vertices - t[:, 3])
    weights = np.c_[a, 1 - a.sum(1)]
    basis = csr_matrix((weights.ravel(), (np.repeat(np.arange(len(vertices)), 4),
                       lattice.simplices[simplex].ravel())), shape=(len(vertices), len(controls)))
    faces = lattice.convex_hull
    regularizer = laplacian(adjacency(controls, faces))
    return basis, regularizer, lattice


def graph(vertices, edges, active, count):
    """Geodesic anchor selection and sparse translations blended on the surface."""
    nearest = np.full(len(vertices), np.inf)
    chosen = [int(active[np.argmax(vertices[active, 1])])]
    paths = []
    for step in range(count):
        distance = dijkstra(edges, directed=False, indices=chosen[-1])
        paths.append(distance)
        nearest = np.minimum(nearest, distance)
        if step < count - 1:
            chosen.append(int(active[np.argmax(nearest[active])]))
    paths = np.asarray(paths).T
    ids = np.argsort(paths, axis=1)[:, :4]
    distance = np.take_along_axis(paths, ids, 1)
    weights = np.where(np.isfinite(distance), np.exp(-np.minimum(distance, 500)**2 / (12**2)), 0)
    weights /= np.maximum(weights.sum(1, keepdims=True), 1e-80)
    basis = csr_matrix((weights.ravel(), (np.repeat(np.arange(len(vertices)), 4), ids.ravel())),
                       shape=(len(vertices), count))
    links = np.argsort(paths[chosen], axis=1)[:, 1:5]
    a = np.repeat(np.arange(count), 4)
    b = links.ravel()
    keep = np.isfinite(paths[chosen][a, b])
    a, b = a[keep], b[keep]
    r = np.arange(len(a))
    regularizer = csr_matrix((np.r_[np.ones(len(a)), -np.ones(len(a))], (np.r_[r, r], np.r_[a, b])),
                             shape=(len(a), count))
    return basis, regularizer


def region_ids(points, lo, hi):
    y = (points[:, 1] - lo) / (hi - lo)
    x = np.abs(points[:, 0])
    label = np.select([y>.875, y>.825, y>.71, y>.62, y>.54, y>.47, y>.29, y>.12, y>.055],
                      [1, 2, 3, 4, 5, 6, 7, 8, 9], default=10)
    label = np.where((x>23) & (y>.43) & (y<.83), np.where(y>.67, 11, np.where(y>.55, 12, 13)), label)
    return label * 2 + ((points[:, 0] > 0) & (label >= 7))


def unit_normals(vertices, faces):
    t = vertices[faces]
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    out = np.zeros_like(vertices)
    for index in faces.T:
        np.add.at(out, index, n)
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)


def samples(vertices, faces, count, seed):
    t = vertices[faces]
    mass = np.linalg.norm(np.cross(t[:,1] - t[:,0], t[:,2] - t[:,0]), axis=1)
    rng = np.random.default_rng(seed)
    ids = rng.choice(len(faces), size=count, p=mass/mass.sum())
    uv = rng.random((count, 2))
    uv = np.where(uv.sum(1)[:,None] > 1, 1-uv, uv)
    a = t[ids]
    return a[:,0] + uv[:,0,None]*(a[:,1]-a[:,0]) + uv[:,1,None]*(a[:,2]-a[:,0])


def fit(vertices, faces, reference, ref_faces, basis, smooth, *, steps=12, weight=3., mode='symmetric',
        max_mm=55., same=False):
    active = np.unique(faces)
    ref_active = np.unique(ref_faces)
    lo, hi = reference[ref_active,1].min(), reference[ref_active,1].max()
    q = samples(reference, ref_faces, 28000, 601)
    source_id = region_ids(vertices, lo, hi)
    target_id = region_ids(q, lo, hi)
    target = cKDTree(q)
    target_normals = unit_normals(reference, ref_faces)[ref_active][cKDTree(reference[ref_active]).query(q)[1]]
    region_trees = {int(region): np.flatnonzero(target_id == region) for region in np.unique(target_id)}
    region_trees = {key: (idx, cKDTree(q[idx])) for key, idx in region_trees.items()}
    identity = eye(basis.shape[1], format='csr')
    penalty = weight * (smooth.T @ smooth) + .06 * identity
    current = vertices.copy()
    curve = []
    for iteration in range(steps):
        d, cor = target.query(current[active])
        if mode in ('regions','normals'):
            for region in np.unique(source_id[active]):
                selected = np.flatnonzero(source_id[active] == region)
                if region in region_trees:
                    ids, tree = region_trees[region]
                    d[selected], local = tree.query(current[active[selected]])
                    cor[selected] = ids[local]
        confidence = np.minimum(1., 2.5 / np.maximum(d, 1e-6))
        if mode == 'normals':
            dots = (target_normals[cor] * unit_normals(current, faces)[active]).sum(1)
            confidence *= np.clip((dots+.25)/1.25, .05, 1)
        want = q[cor]
        if same and mode == 'known':
            want = reference[active]
            confidence = np.ones(len(active))
        src = active
        if mode == 'symmetric':
            subset = np.arange(iteration % 3, len(q), 3)
            _, reverse = cKDTree(current[active]).query(q[subset])
            src = np.r_[active, active[reverse]]
            want = np.vstack((want, q[subset]))
            confidence = np.r_[confidence, np.full(len(reverse), .8)]
        rows = basis[src]
        weighted = rows.multiply(confidence[:,None])
        system = (rows.T @ weighted + penalty).tocsc()
        offsets = factorized(system)(weighted.T @ (want-vertices[src]))
        updated = basis @ offsets
        size = np.linalg.norm(updated,axis=1)
        updated *= np.minimum(1., max_mm / (10*np.maximum(size,1e-9)))[:,None]
        updated = vertices + updated
        change = np.linalg.norm(updated-current,axis=1).mean()
        current = updated
        curve.append({'iteration': iteration+1, 'target_sample_mean_mm': float(target.query(current[active])[0].mean()*10),
                      'correspondence_move_mean_mm': float(change*10)})
        if iteration > 3 and change < .0005:
            break
    return current, curve
