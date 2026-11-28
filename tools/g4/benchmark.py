"""Replay same-family and independent-mask fitting with explicit oracle channels."""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import platform
import resource

import cv2
import numpy as np
from PIL import Image

from evidence import mask_metrics, uncertainty
from fitter import AnatomicalFitter, NativeBasis, RegisteredView
from g1_benchmark import Engine, dump, measurements
from projection import Camera, Raster

KEYS=('yaw','span','center_y','elevation','distance','perspective','roll','dx','dy')
VIEWS=('0','90','180','45')


def calibrated(manifest):
    return Camera(**{k:manifest[k] for k in KEYS})


def load_json(path):
    return json.loads(path.read_text())


def make_view(key,cam,mask,source='calibrated',pose=None,excluded=None,registration_sigma=0.,alternatives=()):
    if not mask.any():
        return None
    encoded=uncertainty(mask,key,source,band=1.5,hidden=excluded)
    scale='independent_metric' if source=='calibrated' else 'unknown_relative'
    return RegisteredView(key,cam,mask,encoded.state,encoded.confidence,source,scale,pose,registration_sigma,alternatives)


def sources(root,g3,case):
    measured=load_json(g3/'measurements/orientation.json')[case]['sector_plus_contour'] if g3 else {}
    observations={'calibrated_rgb':[],'calibrated_m6':[],'calibrated_oracle':[],'g3_sector_rgb':[]}
    for key in VIEWS:
        folder=root/'evidence_maps'/case/key
        if not (folder/'estimated.npz').is_file():
            continue
        cam=calibrated(load_json(folder/'camera.json'))
        raw=dict(np.load(folder/'estimated.npz'))
        rgb = raw['mask_rgb']
        m6 = raw['mask_m6']
        for name,mask in [('calibrated_rgb',rgb),('calibrated_m6',m6),
                          ('calibrated_oracle',np.load(folder/'oracle.npz')['body'])]:
            view=make_view(key,cam,mask)
            if view:
                observations[name].append(view)
        if key in measured:
            sec=measured[key]
            sigma=float(np.median(sec['camera_only_anchor_std_px']))
            v=make_view(key,calibrated(sec['estimated_camera']),rgb,'external_sector',
                        registration_sigma=sigma,alternatives=tuple(sec.get('alternatives',())))
            if v:
                observations['g3_sector_rgb'].append(v)
    return observations


def run_case(a,case,basis,raster,source):
    arrays=dict(np.load(source))
    faces=arrays['faces']
    ref,rt=arrays['reference'],arrays['reference_faces']
    fitter=AnatomicalFitter(basis,raster,faces)
    obs=sources(a.g2,a.g3,case)
    meshes={k:arrays[k] for k in ('reference','reference_faces','faces')}
    metrics={}
    for key in ('E0','E1','rgb_gap','E9','E10'):
        if key in arrays:
            meshes['G2_'+key]=arrays[key]
    settings=[
        ('G4_RGB_IOU','calibrated_rgb','iou',False,True),
        ('G4_RGB','calibrated_rgb','contour',True,True),
        ('G4_M6','calibrated_m6','contour',True,True),
        ('G4_ORACLE','calibrated_oracle','contour',True,True),
        ('G4_G3_SECTOR','g3_sector_rgb','contour',True,True),
    ]
    if not a.quick and case=='A_slim':
        settings.extend([('G4_RGB_BEFORE_REBIND_REFINEMENT','calibrated_rgb','contour',True,True),
                         ('G4_M6_BEFORE_REBIND_REFINEMENT','calibrated_m6','contour',True,True)])
    if a.quick:
        settings=[row for row in settings if row[0]=='G4_RGB']
    if not a.quick and case in ('A_heldout_1','A_high_mass'):
        settings.append(('G4_RGB_SINGLE_SEED','calibrated_rgb','contour',True,False))
    height=ref[rt,1]
    sections=np.linspace(height.min()+.16*np.ptp(height),height.max()-.22*np.ptp(height),15)
    exact=measurements(ref,rt,sections)
    holdout=Camera(135)
    held_mask=raster.draw(holdout,ref,rt,384)
    for key,track,mode,robust,multistart in settings:
        vertices,row=fitter.fit(obs[track],mode=mode,budget=200 if a.quick else 670,robust=robust,multistart=multistart,
                                allow_unanchored_height=key=='G4_G3_SECTOR',
                                refine_rebind=not key.endswith('_BEFORE_REBIND_REFINEMENT'))
        if vertices is not None:
            row['heldout_135']=mask_metrics(raster.draw(holdout,vertices,faces,384),held_mask)
            row['g1_section_errors_mm']=(np.mean(abs(measurements(vertices,faces,sections)-exact),axis=0)*10).tolist()
            if case.startswith('A_'):
                difference=vertices[basis.engine.skin]-ref[basis.engine.skin]
                row['vertex_rmse_mm']=float(10*np.sqrt(np.mean(np.sum(difference**2,axis=1))))
            meshes[key]=vertices
        metrics[key]=row
        print(case,key,row['status'],row.get('checkpoint_rank'),round(row.get('seconds',0),3),flush=True)
    case_out=a.output/case
    case_out.mkdir(exist_ok=True,parents=True)
    dump(case_out/'fitting.json',metrics)
    np.savez_compressed(case_out/(case+'.npz'),**meshes)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--g2',type=Path,required=True)
    p.add_argument('--g3',type=Path)
    p.add_argument('--references',type=Path)
    p.add_argument('--config',type=Path)
    p.add_argument('--raster',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cases',nargs='*')
    p.add_argument('--quick',action='store_true')
    a=p.parse_args()
    cv2.setNumThreads(1)
    e=Engine()
    basis=NativeBasis(e,load_json(a.config or a.g2/'measurements/config.json'))
    raster=Raster(a.raster)
    a.output.mkdir(exist_ok=True,parents=True)
    for source in sorted((a.references or a.g2/'geometry').glob('[AB]_*.npz')):
        if not a.cases or source.stem in a.cases:
            run_case(a,source.stem,basis,raster,source)
    dump(a.output/'runtime.json',dict(platform=platform.platform(),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    main()
