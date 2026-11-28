"""Compose a PNG atlas from actual Blender images and floating-point maps."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from evidence import affine_inverse, aligned_depth, dsine_to_camera


def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype(name, size)


def atlas(title, subtitle, columns, rows, images, destination):
    tile, gap, left, top = 178, 12, 224, 117
    width = left + len(columns) * (tile + gap) + 12
    height = top + 40 + len(rows) * (tile + gap) + 15
    page = Image.new('RGB', (width, height), '#eef1f4')
    painter = ImageDraw.Draw(page)
    painter.text((21, 19), title, font=font(29, True), fill='#162737')
    painter.text((23, 63), subtitle, font=font(16), fill='#31475a')
    for j, heading in enumerate(columns):
        painter.text((left + j * (tile + gap), top), heading, font=font(14, True), fill='#273a4c')
    for i, label in enumerate(rows):
        y = top + 36 + i * (tile + gap)
        painter.multiline_text((20, y + 30), label, font=font(15, True), fill='#172e42', spacing=5)
        for j, img in enumerate(images[i]):
            x = left + j * (tile + gap)
            painter.rounded_rectangle((x, y, x + tile - 1, y + tile - 1), radius=8, fill='#f9fafb')
            if img is not None:
                frame = img.convert('RGBA')
                frame.thumbnail((tile - 8, tile - 8), Image.Resampling.LANCZOS)
                page.paste(frame, (x + (tile - frame.width) // 2, y + (tile - frame.height) // 2), frame)
    page.save(destination, optimize=True)


def map_image(data, mask):
    color = np.uint8(np.clip(data, 0, 1) * 255)
    if color.ndim == 2:
        color = np.stack((np.minimum(1, .25 + .78 * data),
                          np.minimum(1, .25 + .65 * data),
                          np.minimum(1, .65 + .32 * data)), -1)
        color = np.uint8(np.clip(color, 0, 1) * 255)
    return Image.fromarray(np.dstack((color, np.uint8(mask) * 255)))


def depth_atlas(root, output):
    yaws = [0, 90, 180, 270]
    images = []
    for case in ('A_high_mass', 'A_heldout_1'):
        for yaw in yaws[0:2] if case == 'A_high_mass' else yaws:
            with np.load(root / 'maps' / case / f'{yaw}.npz') as data:
                depth, target, valid, fg = (data[name] for name in
                     ('depth_cm', 'normal_right_up_toward', 'valid', 'mask'))
            pred = np.load(root / 'pred' / case / f'{yaw}-depth.npy')
            estimate = aligned_depth(pred, *affine_inverse(pred[valid], depth[valid]))
            surface = dsine_to_camera(np.load(root / 'pred' / case / f'{yaw}-normal.npy'))
            lo, hi = np.percentile(depth[valid], (2, 98))
            scale = lambda z: np.clip((hi - z) / max(hi - lo, 1e-8), 0, 1)
            images.append([Image.open(root / 'rgb' / case / f'{yaw}.png').copy(),
                           map_image(scale(depth), fg), map_image(scale(estimate), fg),
                           map_image((target + 1) / 2, fg), map_image((surface + 1) / 2, fg)])
    atlas('G5 Depth and normal evidence',
          'Blender references · depth display uses an oracle affine fit · positive Z normals face the camera',
          ['Blender RGB', 'Exact depth', 'Predicted depth', 'Exact normals', 'DSINE normals'],
          ['High mass\nFront', 'High mass\nLateral', 'Held-out 1\nFront', 'Held-out 1\nLateral',
           'Held-out 1\nRear', 'Held-out 1\nOpposite lateral'], images, output)


def geometry_atlas(folder, output, subject, surface):
    variants = [('reference', 'Reference'), ('D0', 'D0 · M7'), ('D1', 'D1 · Exact depth'),
                ('D2', 'D2 · Exact normals'), ('D3', 'D3 · Exact both'),
                ('D4', 'D4 · Predicted depth'), ('D5', 'D5 · Predicted normals'),
                ('D6', 'D6 · Predicted both'), ('D7', 'D7 · Local oracle'), ('D8', 'D8 · Local predicted')]
    rows, images = [], []
    for key, label in variants:
        row = surface.get(key)
        if key != 'reference' and not row:
            continue
        if row:
            label += f"\n{row['symmetric_mm']['mean']:.2f} mm"
            if row.get('local_validation') == 'reject and retain parent':
                label += '\nParent retained'
        rows.append(label)
        images.append([Image.open(folder / f'{key}-{view}.png').copy() for view in (0, 90, 180, 45, 'detail')])
    for key, kind, label in [('D7', 'error_mm', 'D7 · Vertex error\n0–25 mm'),
                              ('D7', 'displacement_mm', 'D7 · Proposed move\n0–5 mm')]:
        path = folder / f'{key}-{kind}.png'
        if path.exists():
            rows.append(label)
            images.append([None, None, None, Image.open(path).copy(), None])
    atlas('G5 Blender reconstruction comparisons',
          subject + ' · matched cameras and framing · symmetric surface distance in millimetres',
          ['Front', 'Lateral', 'Rear', 'Three-quarter', 'Torso detail'], rows, images, output)


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['channels', 'geometry'])
    parser.add_argument('folder', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--measurements', type=Path)
    parser.add_argument('--subject')
    args = parser.parse_args()
    if args.mode == 'channels':
        depth_atlas(args.folder, args.output)
    else:
        geometry_atlas(args.folder, args.output, args.subject,
                       json.loads(args.measurements.read_text())[args.subject])
