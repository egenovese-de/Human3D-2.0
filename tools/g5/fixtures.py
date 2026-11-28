"""Regenerate the original G4 cohort without running its fitting benchmark."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import runpy

import numpy as np
from g1_benchmark import Engine, triangulate
from references import main as heldout_references

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('g4', type=Path)
    parser.add_argument('historical', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    engine = Engine()
    # Execute only the pinned G1 profile declaration, with the same resolver.
    source = (args.g4 / 'tools/g1/g1_benchmark.py').read_text()
    start = source.index('    global_names=')
    end = source.index('    equiv +=', start)
    setup = source[start:end]
    equiv_start = setup.index('    paired=')
    genetics_start = setup.index('    genetics=')
    namespace = {'e': engine}
    exec('def profiles():\n' + setup[:equiv_start] + setup[genetics_start:] +
         '    return dict(genetics[:4])\n', namespace)
    faces = triangulate(engine.faces)
    recipes = namespace['profiles']()
    for name, parameters in recipes.items():
        ref = engine.native(parameters)[0] * 10
        np.savez_compressed(args.output / f'A_{name}.npz', reference=ref,
                            reference_faces=faces, faces=faces)
    import sys
    sys.argv = ['references.py', str(args.output)]
    heldout_references()
    manifest = json.loads((args.g4 / 'DOCS/g2/G2_DATASET_MANIFEST.json').read_text())
    native = engine.base[engine.skin]
    for record in manifest['families']['B']['cases']:
        preset = record['preset']
        sex = 'female' if preset.startswith('f') else 'male'
        source_file = args.historical / f'MBLab_human_{sex}_{preset}_bend0' / 'mesh.json'
        raw = source_file.read_bytes()
        if sha256(raw).hexdigest() != record['source_mesh_sha256']:
            raise ValueError(f'Unexpected historical mesh {source_file}')
        payload = json.loads(raw)
        xyz = np.asarray(payload['vertices'])
        scale = np.ptp(native[:, 1]) * 10 / np.ptp(xyz[:, 2])
        ref = np.c_[xyz[:, 0], xyz[:, 2] - xyz[:, 2].min(), -xyz[:, 1]] * scale
        ref[:, 1] += native[:, 1].min() * 10
        np.savez_compressed(args.output / (record['id'] + '.npz'), reference=ref,
                            reference_faces=triangulate(payload['faces']), faces=faces)
    (args.output / 'original-configurations.json').write_text(json.dumps(recipes, indent=2))
    print('Generated:', sorted(p.stem for p in args.output.glob('*.npz')), flush=True)

if __name__ == '__main__':
    main()
