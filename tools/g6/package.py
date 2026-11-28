"""Publish G6 results, publishable Family A samples and verified archives."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile

from PIL import Image


def main(repo,results,delivery):
    entries={}
    def put(name,path):
        entries[name]=path
    for f in sorted((repo/'DOCS/g6').glob('*')):
        put(f'docs/{f.name}',f)
    for f in sorted((repo/'tools/g6').glob('*')):
        if f.is_file():
            put(f'source/{f.name}',f)
    put('source/ci/g6-geometry-capacity.yml',repo/'.github/workflows/g6-geometry-capacity.yml')
    for f in sorted(delivery.glob('G6_*.png')):
        with Image.open(f) as image:
            assert image.width>300 and image.height>250
            image.verify()
        put(f'atlases/{f.name}',f)
    for f in sorted(results.glob('*.json')):
        put(f'measurements/{f.name}',f)
    for folder in ('study','photo','posture','oracle','volume','export','baseline'):
        for f in sorted((results/folder).glob('**/*.json')):
            if folder=='baseline' and f.name!='attempt.json':
                continue
            if folder not in ('baseline','export') and f.name not in ('fit.json','surface.json','landmarks.json'):
                continue
            put('measurements/'+str(f.relative_to(results)),f)
    for f in sorted((results/'render').glob('*/*')):
        if f.is_file():
            put(str(f.relative_to(results)),f)
    for case,tag in [('A_slim','accepted.npz'),('A_adult_asymmetric','proposals.npz')]:
        put(f'geometry/{case}/{tag}',results/'study'/case/tag)
    put('geometry/A_heldout_1/poses.npz',results/'poses.npz')
    for f in sorted((results/'export'/'A_slim').glob('*')):
        if f.suffix in ('.usd','.blend'):
            put('geometry/A_slim/export/'+f.name,f)
    for f in sorted((results/'logs').glob('*.log')):
        put(f'logs/{f.name}',f)
    manifest={}
    destination=delivery/'Human3D_G6_EVIDENCE.zip'
    with ZipFile(destination,'w',compression=ZIP_DEFLATED,compresslevel=5) as zip_file:
        for name,p in sorted(entries.items()):
            if not p.is_file():
                raise ValueError(f'Missing evidence {name}')
            if name.startswith(('geometry/','render/')) and any(p.startswith(('B_female','B_male')) for p in Path(name).parts):
                raise ValueError('restricted Family B geometry')
            data=p.read_bytes()
            manifest[name]=sha256(data).hexdigest()
            zip_file.writestr(name,data)
        zip_file.writestr('SHA256SUMS.json',json.dumps(manifest,indent=2))
    with ZipFile(destination) as zip_file:
        assert zip_file.testzip() is None
        for name,h in manifest.items():
            assert sha256(zip_file.read(name)).hexdigest()==h
    print(len(entries),destination.stat().st_size,sha256(destination.read_bytes()).hexdigest(),destination)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('repo','results','delivery'):
        p.add_argument(k,type=Path)
    main(**vars(p.parse_args()))
