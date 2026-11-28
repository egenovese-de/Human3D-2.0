"""Execute the pinned DSINE normal checkpoint on CPU."""
import json
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.request import urlretrieve

import numpy as np
import psutil

from evidence import dsine_to_camera
from predict import normal_model

WEIGHT = ('https://huggingface.co/camenduru/DSINE/resolve/'
          'eb7c7991e19351cef4ead99811fc1117595b6bff/dsine.pt?download=true')


def main(source, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    y, x = np.indices((384, 384))
    rgb = np.full((384, 384, 3), 210, np.uint8)
    target = ((x - 166) ** 2 + (y - 214) ** 2) < 66 ** 2
    rgb[target] = [46, 90, 140]
    with TemporaryDirectory() as folder:
        weight = Path(folder) / 'dsine.pt'
        urlretrieve(WEIGHT, weight)
        start = perf_counter()
        predictor = normal_model(weight, source)
        result = {'platform': platform.platform(), 'machine': platform.machine(),
                  'initialization_s': perf_counter() - start, 'model_bytes': weight.stat().st_size}
        durations = []
        for _ in range(3):
            start = perf_counter()
            values = dsine_to_camera(predictor(rgb, 384))
            durations.append(perf_counter() - start)
            if (values.shape != (384, 384, 3) or not np.isfinite(values).all()
                    or np.max(np.abs(np.linalg.norm(values, axis=2) - 1)) > 1e-5):
                raise ValueError('Invalid normal smoke prediction.')
        result['cpu_384_inference_seconds'] = durations
        result['working_set_rss_bytes_after_runs'] = psutil.Process().memory_info().rss
        output.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
