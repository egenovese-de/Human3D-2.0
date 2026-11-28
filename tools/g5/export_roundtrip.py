"""Export accepted bounded-local candidates with the qualified M7 USD writer."""
import argparse
import json
from pathlib import Path

import numpy as np
from pxr import Usd, UsdGeom, UsdSkel

from human3d.alignment import Alignment, Camera
from human3d.fitting import Fit
from human3d.frozen_body import load_project_body
from human3d.session import Session
from human3d.usd_export import export_body


def invariants(path):
    stage = Usd.Stage.Open(str(path))
    mesh = next(UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
    binding = UsdSkel.BindingAPI(mesh.GetPrim())
    uv = UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st')
    return [tuple(mesh.GetFaceVertexCountsAttr().Get()), tuple(mesh.GetFaceVertexIndicesAttr().Get()),
            tuple(map(tuple, uv.Get())), tuple(uv.GetIndices()),
            tuple(binding.GetJointIndicesPrimvar().Get()), tuple(binding.GetJointWeightsPrimvar().Get())]


def main(out, case, measurements):
    folder = out / 'roundtrip' / case
    folder.mkdir(parents=True, exist_ok=True)
    source = out / 'calibrated' / case
    session = Session(out / 'baseline' / case / 'calibrated' / 'project')
    body = load_project_body(session.store)
    fit = Fit({}, 0., 0.)
    alignment = Alignment(Camera(0, 1, 0j, 1), 0, {})
    measurements = json.loads(measurements.read_text())[case]
    summary, original = {}, None
    with np.load(source / 'meshes.npz') as saved:
        for key in ('D0', 'D7', 'D8'):
            if (key not in saved.files or measurements[key].get('local_validation') == 'reject and retain parent'):
                continue
            mesh = body['mesh'] | {'vertices': (saved[key] / 10).tolist()}
            artifact = folder / f'{case}-{key}.usd'
            export_body(artifact, body | {'mesh': mesh}, fit, alignment)
            guard = invariants(artifact)
            if original is None:
                original = guard
            if guard != original:
                raise ValueError(f'{case}/{key} changed UV, topology or skin data.')
            summary[key] = {'topology_uv_and_skin_unchanged_vs_d0': True, 'usd_filename': artifact.name}
    (folder / 'm7_export_validation.json').write_text(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('case')
    parser.add_argument('measurements', type=Path)
    args = parser.parse_args()
    main(args.output, args.case, args.measurements)
