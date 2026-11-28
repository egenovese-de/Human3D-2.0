"""Export retained G6 candidates through the unchanged M7 writer."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from export_roundtrip import invariants
from human3d.alignment import Alignment,Camera
from human3d.fitting import Fit
from human3d.frozen_body import load_project_body
from human3d.native_rig import validate_rebind
from human3d.session import Session
from human3d.usd_export import export_body


def main(args):
    body=load_project_body(Session(args.baseline/args.input.name/'calibrated'/'project').store)
    rest=Alignment(Camera(0,1,0j,1.),0,{})
    args.output.mkdir(parents=True,exist_ok=True)
    writer=Fit({},0.,0.)
    details={}
    parent=None
    with np.load(args.input/'accepted.npz') as f:
        for name in ('D0','R2_fine'):
            begin=perf_counter()
            v=f[name]/10
            joints=validate_rebind(body,v)
            checked=perf_counter()
            mesh=body['mesh']|{'vertices':v.tolist()}
            usd=args.output/(name+'.usd')
            export_body(usd,body|{'mesh':mesh},writer,rest)
            attrs=invariants(usd)
            if parent is None:
                parent=attrs
            if attrs!=parent:
                raise ValueError(f'{name} changes canonical index, UV or skin invariants')
            details[name]={'unchanged_index_uv_skin':True,'joint_count':len(joints),
                           'bytes':usd.stat().st_size,'validate_rebind_s':checked-begin,
                           'export_and_verification_s':perf_counter()-checked}
    (args.output/'invariants.json').write_text(json.dumps(details,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('input','baseline','output'):
        parser.add_argument(key,type=Path)
    main(parser.parse_args())
