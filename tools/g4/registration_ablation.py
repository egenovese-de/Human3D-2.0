"""Separate orientation, camera framing, and absolute-scale errors in G4."""
from dataclasses import replace
from pathlib import Path
import sys

import cv2
import numpy as np

from benchmark import make_view, load_json, sources
from fitter import AnatomicalFitter, NativeBasis
from g1_benchmark import Engine, dump
from projection import Raster


def main(g2,g3,lib,out):
    cv2.setNumThreads(1)
    e=Engine()
    basis=NativeBasis(e,load_json(g2/'measurements/config.json'))
    raster=Raster(lib)
    for file in sorted((g2/'geometry').glob('A_*.npz')):
        case=file.stem
        arrays=dict(np.load(file))
        obs=sources(g2,g3,case)
        estimated={v.key:v for v in obs['g3_sector_rgb']}
        oracle={v.key:v for v in obs['calibrated_rgb']}
        shared=sorted(estimated.keys() & oracle.keys())
        partials={}
        for knob in ('CAMERA_YAW_ONLY','CAMERA_FRAME_ONLY'):
            values=[]
            for key in shared:
                ref=oracle[key]
                alt=estimated[key]
                camera=replace(ref.camera,yaw=alt.camera.yaw) if knob=='CAMERA_YAW_ONLY' else                     replace(ref.camera,span=alt.camera.span,dx=alt.camera.dx,dy=alt.camera.dy)
                values.append(replace(ref,camera=camera,camera_source='calibrated_sector_control'))
            partials[knob]=values
        partials['G4_G3_RELATIVE']=list(estimated.values())
        fitter=AnatomicalFitter(basis,raster,arrays['faces'])
        payload={k:arrays[k] for k in ('reference','faces','reference_faces')}
        runs={}
        for name,bundle in partials.items():
            mesh,result=fitter.fit(bundle,budget=500)
            runs[name]=result
            if mesh is not None:payload[name]=mesh
            print(case,name,result['status'],result.get('locked_controls'),round(result.get('seconds',0),2),flush=True)
        folder=out/case
        folder.mkdir(exist_ok=True,parents=True)
        dump(folder/'registration_ablation.json',runs)
        np.savez_compressed(folder/(case+'.npz'),**payload)


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
