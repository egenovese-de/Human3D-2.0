"""Fit geometry from a manifest of registered evidence maps.

All view files must already use the declared normalized pixel frame. Output contains
canonical points and topology; it does not apply an observation or export pose.
"""
import argparse
from pathlib import Path
import tempfile
import os

import cv2
import numpy as np

from benchmark import calibrated, load_json
from fitter import AnatomicalFitter, NativeBasis, RegisteredView
from g1_benchmark import Engine, dump, triangulate
from projection import Raster


def read_views(path):
    doc=load_json(path)
    if doc['schema_version']!=1:
        raise ValueError('unsupported observation manifest schema')
    keys=set()
    for entry in doc['views']:
        key=entry['key']
        if key in keys:
            raise ValueError('duplicate observation key')
        keys.add(key)
        source=(path.parent/entry['evidence']).resolve()
        if not source.is_relative_to(path.parent.resolve()):
            raise ValueError('evidence must be within the manifest directory')
        with np.load(source,allow_pickle=False) as data:
            yield RegisteredView(key,calibrated(entry['camera']),data['mask'].astype(bool),
                   data['states'],data['confidence'],entry['camera_source'],entry['scale_source'],
                   np.asarray(entry['pose'],float) if entry.get('pose') is not None else None,
                   entry.get('registration_sigma_px',0.),tuple(entry.get('alternatives',())),
                   data['outer_only'].astype(bool) if 'outer_only' in data else None)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path)
    p.add_argument('basis',type=Path)
    p.add_argument('raster',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--budget',type=int,default=670)
    args=p.parse_args()
    cv2.setNumThreads(1)
    engine=Engine()
    basis=NativeBasis(engine,load_json(args.basis))
    faces=triangulate(engine.faces)
    fitter=AnatomicalFitter(basis,Raster(args.raster),faces)
    views=list(read_views(args.manifest))
    canonical,result=fitter.fit(views,budget=args.budget)
    dest=args.output.resolve()
    if dest.exists():
        raise FileExistsError('result directory already exists')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as scratch:
        staged=Path(scratch)/'result'
        staged.mkdir()
        if canonical is not None:
            np.savez_compressed(staged/'canonical.npz',canonical_cm=canonical,faces=faces)
        dump(staged/'result.json',result)
        os.replace(staged,dest)
    print(result['status'])


if __name__=='__main__':
    main()
