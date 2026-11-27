"""Create held-out anatomy combinations not supplied to the photographic fitter."""
import argparse
import json
from pathlib import Path
import numpy as np
from g1_benchmark import Engine, triangulate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    e = Engine()
    faces = triangulate(e.faces)
    configurations = [
        {'Gender': .24, 'Age': .59, 'Weight': .57, 'Muscle': .71, 'Height': .55, 'BreastSize': .68},
        {'Gender': .78, 'Age': .76, 'Weight': .81, 'Muscle': .35, 'Height': .34, 'BodyProportions': .57},
    ]
    local = [
        {'hip/hip-scale-horiz': .24, 'stomach/stomach-pregnancy': -.18, 'buttocks/buttocks-volume': .28},
        {'torso/torso-scale-depth': -.22, 'armslegs/l-upperarm-scale-horiz': .31,
         'measure/measure-thigh-circ': .2},
    ]
    cases = {}
    for i,(macro, region) in enumerate(zip(configurations, local), 1):
        params = {e.mac[key]:value for key,value in macro.items()}
        for stem,value in region.items():
            matches = [key for key in e.mods if key.startswith(stem+'-') and e.defs[key]]
            if len(matches) == 1:
                params[matches[0]] = value
        name = f'A_heldout_{i}'
        cases[name] = params
        reference = e.native(params)[0]*10
        np.savez_compressed(args.directory/(name+'.npz'), reference=reference, reference_faces=faces,
                            faces=faces)
    (args.directory/'generation-only.json').write_text(json.dumps(cases,indent=2)+'\n')

if __name__ == '__main__':
    main()
