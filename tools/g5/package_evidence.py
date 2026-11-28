"""Build and verify a G5 delivery without model weights or restricted geometry."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np

from evidence import dsine_to_camera


def main(source, outputs, delivery):
    destination = delivery / 'Human3D_G5_EVIDENCE.zip'
    entries = {}
    for path in sorted((source/'DOCS/g5').glob('*')):
        entries['reports/' + path.name] = path
    for path in sorted((source/'tools/g5').glob('*')):
        if path.is_file():
            entries['source/' + path.name] = path
    entries['source/ci/g5-depth-normals.yml'] = source/'.github/workflows/g5-depth-normals.yml'
    for name in ('G5_Blender_Comparison.png', 'G5_Depth_Normal_Atlas.png'):
        entries['atlases/' + name] = delivery/name
    for folder, path in [('oracle', outputs/'maps/quality.json'), ('oracle', outputs/'rays.json'),
                         ('conditions', outputs/'appearance-quality.json'), ('conditions', outputs/'stress/fit.json')]:
        entries[f'measurements/{folder}/{path.name}'] = path
    for profile in outputs.glob('*surface.json'):
        entries['measurements/' + profile.name] = profile
    for profile in sorted((outputs/'pred').glob('*runtime.json')):
        entries['measurements/models/' + profile.name] = profile
    for category in ('calibrated', 'estimated', 'estimated-fov', 'robustness'):
        for path in sorted((outputs/category).rglob('fit.json')):
            entries[f'measurements/fits/{category}/{path.relative_to(outputs/category)}'] = path
    for path in sorted((outputs/'roundtrip').glob('*/*.json')):
        entries['measurements/roundtrip/' + str(path.relative_to(outputs/'roundtrip'))] = path
    for path in sorted((outputs/'ci').glob('*.json')):
        entries[f'measurements/ci/{path.name}'] = path
    for path in sorted((outputs/'logs').glob('*.log')):
        if path.stat().st_size:
            entries[f'logs/{path.name}'] = path
    for path in sorted((outputs/'rgb').glob('A_*/*.png')):
        entries[f'rgb/{path.relative_to(outputs/"rgb")}'] = path
    for path in sorted((outputs/'appearance_rgb').glob('*/*.png')):
        entries[f'rgb/appearance/{path.relative_to(outputs/"appearance_rgb")}'] = path
    for case in ('A_high_mass','A_heldout_1','A_slim'):
        entries[f'geometry/{case}/snapshots_and_local_proposals.npz'] = outputs/'calibrated'/case/'meshes.npz'
    entries['geometry/A_high_mass/atlas_render_inputs.npz'] = outputs/'visual/approved.npz'
    for path in sorted((outputs/'visual/renders').glob('*.png')):
        entries[f'renders/A_high_mass/{path.name}'] = path
    converted = outputs/'public_channels'
    for case in ('A_high_mass', 'A_heldout_1'):
        for yaw in (0,90,180,270,45,22,112,202,292):
            stem = f'{case}/{yaw}'
            exact = outputs/'maps'/case/f'{yaw}.npz'
            entries[f'channels/{stem}/exact.npz'] = exact
            depth, normals = [outputs/'pred'/case/f'{yaw}-{channel}.npy' for channel in ('depth','normal')]
            if depth.exists() and normals.exists():
                target = converted/case/f'{yaw}.npz'
                target.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(target, relative_inverse_depth=np.load(depth, allow_pickle=False),
                   dsine_normal_right_up_toward=dsine_to_camera(np.load(normals, allow_pickle=False)))
                entries[f'channels/{stem}/predicted.npz'] = target
    manifest = {}
    with ZipFile(destination, 'w', compression=ZIP_DEFLATED, compresslevel=5) as archive:
        for name, file in sorted(entries.items()):
            data = file.read_bytes()
            archive.writestr(name, data)
            manifest[name] = sha256(data).hexdigest()
        archive.writestr('SHA256SUMS.json', json.dumps(manifest, indent=2))
        archive.writestr('README.md', '# Human3D G5 evidence\n\n'
            'Start with reports/G5_EXECUTIVE_REPORT.md. Geometry snapshots contain canonical centimetres and fixed triangle identities. '
            'A local trial can be rejected even if its proposed mesh is present. Use the fit and surface measurements for its accepted disposition. '
            'Blender atlas inputs reflect parent retention for rejected local trials. Family B is distributed as numeric evidence. '
            'Model checkpoints are provisioned separately. This ZIP excludes MB-Lab source geometry and model weights.\n')
    with ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        for name, digest in manifest.items():
            if sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f'ZIP entry digest verification failed: {name}')
            if name.startswith(('geometry/','channels/','rgb/','renders/')) and '/B_' in name:
                raise ValueError(f'Unexpected independent source asset: {name}')
    print(destination, len(manifest), destination.stat().st_size, sha256(destination.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source','outputs','delivery'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    main(args.source, args.outputs, args.delivery)
