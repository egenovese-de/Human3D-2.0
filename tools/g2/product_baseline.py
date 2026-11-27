"""Reconstruct via the M6 project/session path and preserve abstentions."""
import argparse
from pathlib import Path
import os
import tempfile
import time
import numpy as np
from PIL import Image
from g1_benchmark import dump
from photographic import rgb_image
from human3d.bootstrap import ASSETS, MORPH_ASSETS, TORSO_ASSETS, freeze_project
from human3d.frozen_body import deform_vertices, load_frozen_body
from human3d.session import Session
from human3d.vision import PoseLandmarker


def main():
    p = argparse.ArgumentParser()
    p.add_argument('inputs',type=Path)
    p.add_argument('references',type=Path)
    p.add_argument('model',type=Path)
    p.add_argument('out',type=Path)
    a = p.parse_args()
    a.out.mkdir(exist_ok=True,parents=True)
    data = Path(os.environ['U'])/'data'
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        assets = root/'assets'
        assets.mkdir()
        admitted = ASSETS | MORPH_ASSETS | TORSO_ASSETS
        for f in data.rglob('*'):
            if f.name in admitted:
                (assets/f.name).symlink_to(f.resolve())
        detector = PoseLandmarker(a.model,segmentation=True)
        for case_path in sorted(a.inputs.glob('[AB]_*')):
            case = case_path.name
            blender_inputs = [case_path/(str(angle)+'.png') for angle in (0,90,180,45)]
            paths = [root/(case+'-'+file.name) for file in blender_inputs]
            for source,target in zip(blender_inputs,paths):
                if source.exists():
                    rgb,_ = rgb_image(np.array(Image.open(source).convert('RGBA')),'plain')
                    Image.fromarray(rgb).save(target)
            if not all(f.exists() for f in paths):
                continue
            s = Session(root/case,create=True)
            frozen = freeze_project(s.store,assets)
            s.ingest(paths)
            started = time.perf_counter()
            photos = s.store.load().photos.photos
            failures = []
            for photo,path in zip(photos,paths):
                try:
                    s.detect_photo(photo.id, detector)
                except (ValueError,RuntimeError) as exc:
                    failures.append([path.stem,str(exc)])
            evidence = s.shared_evidence()
            row = dict(detection_seconds=time.perf_counter()-started, admitted_views=len(evidence.views),
                       unresolved=evidence.unresolved,detection_failures=failures)
            started = time.perf_counter()
            try:
                result = s.fit_shared()
                body = load_frozen_body(s.store.directory/'frozen'/(frozen+'.json'))
                vertices = np.array(deform_vertices(body,result.fit.controls))*10
                ref = dict(np.load(a.references/(case+'.npz')))
                np.savez_compressed(a.out/(case+'.npz'),reference=ref['reference'],
                                    reference_faces=ref['reference_faces'],faces=ref['faces'],M6_product=vertices)
                row.update(status='PASS',controls=result.fit.controls,scores=result.scores,
                           aligned_views=len(result.alignments),fit_digest=s.store.load().shared_fit_digest)
            except (ValueError,RuntimeError) as exc:
                row.update(status='ABSTAINED',reason=str(exc))
            row['fitting_seconds'] = time.perf_counter()-started
            dump(a.out/(case+'.json'),row)
            print(case,row['status'],row.get('reason'),flush=True)

if __name__ == '__main__':
    main()
