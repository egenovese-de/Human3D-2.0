from pathlib import Path
import sys
import numpy as np

from baseline import engine_b

runtime, rgb, output = map(Path, sys.argv[1:4])
for case in sys.argv[4:] or sorted(p.name for p in rgb.iterdir() if p.is_dir()):
    for estimated in (False, True):
        work = output / case / ('estimated' if estimated else 'calibrated')
        try:
            vertices, _, fit, _, _, _ = engine_b(runtime, rgb / case, work, estimated=estimated)
            np.save(work / 'D0.npy', vertices)
            print(case, 'estimated' if estimated else 'calibrated', fit, flush=True)
        except Exception as error:
            print(case, 'estimated' if estimated else 'calibrated', repr(error), flush=True)
