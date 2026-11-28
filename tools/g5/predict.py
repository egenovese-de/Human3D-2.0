"""Run one pinned CPU predictor at a time over the unmasked RGB fixtures."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
try:
    import resource
except ImportError:
    resource = None
import sys
from time import perf_counter
from types import SimpleNamespace

import cv2
import numpy as np
from PIL import Image

from evidence import CONFIG, SIZE, resized, unit

DEPTH_SHA = 'afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c'
MEAN = np.array([.485, .456, .406], np.float32)
STD = np.array([.229, .224, .225], np.float32)


def depth_model(weight):
    import onnxruntime as ort

    if sha256(weight.read_bytes()).hexdigest() != DEPTH_SHA:
        raise ValueError('Unexpected depth checkpoint')
    options = ort.SessionOptions()
    options.intra_op_num_threads = CONFIG['cpu_threads']
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(weight), options, providers=['CPUExecutionProvider'])
    assert session.get_providers() == ['CPUExecutionProvider']

    def infer(rgb, size):
        image = resized(rgb, size, cv2.INTER_CUBIC)
        pixels = (image.astype(np.float32) / 255 - MEAN) / STD
        raw = session.run(None, {'pixel_values': pixels.transpose(2, 0, 1)[None]})[0][0]
        return resized(raw, SIZE, cv2.INTER_CUBIC)
    return infer


def normal_model(weight, source):
    import torch

    if sha256(weight.read_bytes()).hexdigest() != '629472c66ea9ec83bab6ba7c957ad7d983bb9c91063a54ad74ff5b8229cbf22f':
        raise ValueError('Unexpected normal checkpoint')
    torch.set_num_threads(CONFIG['cpu_threads'])
    torch.set_num_interop_threads(1)
    sys.path.insert(0, str(source.resolve()))
    from models.dsine import v02

    # Override upstream's CUDA-only pixel-grid placement and disable the
    # redundant backbone download. The complete checkpoint loads strictly.
    encoder = v02.Encoder
    v02.Encoder = lambda B, pretrained: encoder(B=B, pretrained=False)
    v02.get_pixel_coords = lambda h, w: torch.from_numpy(
        np.stack((*np.meshgrid(np.arange(w, dtype=np.float32) + .5,
                               np.arange(h, dtype=np.float32) + .5),
                  np.ones((h, w), np.float32)))[None]).as_subclass(CpuPixelGrid)
    args = SimpleNamespace(NNET_encoder_B=5, NNET_decoder_NF=2048, NNET_decoder_BN=False,
        NNET_decoder_down=8, NNET_learned_upsampling=True, NRN_prop_ps=5, NRN_num_iter_train=5,
        NRN_num_iter_test=5, NRN_ray_relu=True, NNET_output_dim=3, NNET_feature_dim=64,
        NNET_hidden_dim=64)

    class CpuPixelGrid(torch.Tensor):
        def to(self, arg, *args, **kwargs):
            if arg == 0:
                return self.as_subclass(torch.Tensor)
            return super().to(arg, *args, **kwargs)

    model = v02.DSINE_v02(args).eval()
    state = torch.load(weight, map_location='cpu', weights_only=True)
    model.load_state_dict({key.removeprefix('module.'): value for key, value in state['model'].items()},
                          strict=True)

    def infer(rgb, size):
        image = resized(rgb, size, cv2.INTER_AREA)
        pixels = (image.astype(np.float32) / 255 - MEAN) / STD
        focal = size * CONFIG['main_camera_cm']['distance'] / CONFIG['main_camera_cm']['span']
        intrinsics = torch.tensor([[[focal, 0, size / 2], [0, focal, size / 2], [0, 0, 1]]])
        with torch.inference_mode():
            raw = model(torch.from_numpy(pixels.transpose(2, 0, 1)[None]), intrins=intrinsics)[-1]
        normal = raw[0].permute(1, 2, 0).numpy()
        normal[..., 1] *= -1
        return unit(resized(normal, SIZE, cv2.INTER_LINEAR)).astype(np.float32)
    return infer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['depth', 'normal'])
    parser.add_argument('weight', type=Path)
    parser.add_argument('images', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--cases', nargs='*')
    options = parser.parse_args()
    cv2.setNumThreads(1)
    start = perf_counter()
    infer = depth_model(options.weight) if options.kind == 'depth' else normal_model(options.weight, options.source)
    report = {'initialization_s': perf_counter() - start, 'weight_bytes': options.weight.stat().st_size,
              'sha256': sha256(options.weight.read_bytes()).hexdigest(), 'cpu_threads': CONFIG['cpu_threads'],
              'images': {}}
    options.output.mkdir(parents=True, exist_ok=True)
    for path in sorted(options.images.glob('*/*.png')):
        case = path.parent.name
        if options.cases and case not in options.cases:
            continue
        if path.stem.isdigit() and int(path.stem) not in CONFIG['fit_yaw_deg']:
            continue
        rgb = np.asarray(Image.open(path).convert('RGB'))
        folder = options.output / case
        folder.mkdir(exist_ok=True)
        for size in ((392, 280) if options.kind == 'depth' else (384, 256)):
            primary = size >= 384
            if not primary and (case not in CONFIG['development'] or path.stem not in ('0', '90')):
                continue
            start = perf_counter()
            result = infer(rgb, size)
            elapsed = perf_counter() - start
            if not np.isfinite(result).all():
                raise ValueError(f'Nonfinite prediction: {path}')
            suffix = '' if primary else f'-{size}'
            output = folder / f'{path.stem}-{options.kind}{suffix}.npy'
            np.save(output, result.astype(np.float32))
            report['images'][str(output.relative_to(options.output))] = {'seconds': elapsed,
                'input_size': size, 'bytes': output.stat().st_size, 'photo_sha256': sha256(path.read_bytes()).hexdigest()}
            print(case, path.stem, size, round(elapsed, 4), flush=True)
    report['peak_rss_kib_linux'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None
    (options.output / (options.kind + '-runtime.json')).write_text(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
