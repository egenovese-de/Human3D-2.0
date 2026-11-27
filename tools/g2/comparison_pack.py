"""Assemble comparable mesh variants and the admitted source UV loop table."""
import argparse
import os
from pathlib import Path
import numpy as np
from human3d.bootstrap import _mesh


def main():
    a = argparse.ArgumentParser()
    a.add_argument('experiment',type=Path)
    a.add_argument('output',type=Path)
    a.add_argument('case')
    a.add_argument('best')
    args = a.parse_args()
    exp, case = args.experiment,args.case
    source = dict(np.load(exp/'meshes'/(case+'.npz')))
    data = {key:source[key] for key in ('reference','reference_faces','faces','E1','E9')}
    data['best'] = source[args.best]
    product = exp/'product'/(case+'.npz')
    if product.is_file():
        data['M6_product'] = np.load(product)['M6_product']
    else:
        data['E0'] = source['E0']
    direct = exp/'direct'/(case+'.npz')
    if direct.exists():
        data['E10'] = np.load(direct)['E10']
    elif 'E10' in source:
        data['E10'] = source['E10']
    if case.startswith('A_'):
        obj = Path(os.environ['U'])/'data/3dobjs/base.obj'
        mesh = _mesh(obj.read_text())
        texcoords = np.asarray(mesh['texcoords'])
        uv = [f['corners'] for f in mesh['faces'] if f['group']=='body']
        tri = np.asarray([[poly[j] for j in (0,i,i+1)] for poly in uv for i in range(1,len(poly)-1)])
        if not np.array_equal(tri[:,:,0],data['faces']):
            raise ValueError('UV index order mismatch')
        data['uv_loops'] = texcoords[tri[:,:,1].ravel()]
    resid = exp/'scores'/f'{case}-{args.best}-vertex-residual.npy'
    if resid.exists():
        data['surface_residual_mm'] = np.load(resid)
    args.output.parent.mkdir(exist_ok=True,parents=True)
    np.savez_compressed(args.output,**data)


if __name__=='__main__':
    main()
