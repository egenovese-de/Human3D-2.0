"""A Windows/Linux ONNX CPU smoke with independent cold and warm timings."""
import json
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.request import urlretrieve

import numpy as np
import psutil

from predict import depth_model

WEIGHT = ('https://huggingface.co/onnx-community/depth-anything-v2-small/'
          'resolve/4472b7362082/onnx/model.onnx?download=true')


def main(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    y, x = np.indices((384, 384))
    rgb = np.full((384, 384, 3), 210, np.uint8)
    near = ((x - 166) ** 2 + (y - 214) ** 2) < 66 ** 2
    rgb[near] = [46, 90, 140]
    with TemporaryDirectory() as folder:
        weight = Path(folder) / 'depth.onnx'
        urlretrieve(WEIGHT, weight)
        start = perf_counter()
        predictor = depth_model(weight)
        result = {'platform': platform.platform(), 'machine': platform.machine(),
                  'initialization_s': perf_counter() - start, 'model_bytes': weight.stat().st_size}
        images = []
        for _ in range(3):
            start = perf_counter()
            values = predictor(rgb, 392)
            images.append(perf_counter() - start)
            if values.shape != (384, 384) or not np.isfinite(values).all() or np.ptp(values) == 0:
                raise ValueError('Invalid depth smoke prediction.')
        result['cpu_392_inference_seconds'] = images
        result['working_set_rss_bytes_after_runs'] = psutil.Process().memory_info().rss
        output.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
