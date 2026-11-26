"""Measure closed section-loop circumference from common metric geometry packs."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np


def circumference(vertices, faces, z):
    """Select the largest closed contour that crosses the centerline."""
    vertices = np.asarray(vertices)
    links = defaultdict(set)
    points = {}
    for face in faces:
        points_on_plane = []
        polygon = vertices[list(face)]
        for a, b in zip(polygon, np.roll(polygon, 1, axis=0)):
            if (a[2] < z) == (b[2] < z):
                continue
            p = a[:2] + (z - a[2]) / (b[2] - a[2]) * (b[:2] - a[:2])
            key = tuple(np.rint(p * 1e7).astype(int))
            points[key] = p
            points_on_plane.append(key)
        for a, b in zip(points_on_plane[::2], points_on_plane[1::2]):
            if a != b:
                links[a].add(b)
                links[b].add(a)
    visited = set()
    rings = []
    for start in links:
        if start in visited:
            continue
        component = {start}
        pending = [start]
        while pending:
            for endpoint in links[pending.pop()] - component:
                component.add(endpoint)
                pending.append(endpoint)
        visited.update(component)
        if len(component) < 3 or any(len(links[node]) != 2 for node in component):
            continue
        x = [points[node][0] for node in component]
        if min(x) >= 0 or max(x) <= 0:
            continue
        layout = sum(np.linalg.norm(points[a] - points[b])
                     for a in component for b in links[a]) / 2
        rings.append(float(layout * 1000))
    return max(rings, default=None)


def main(packs, output):
    output.mkdir(exist_ok=True)
    for path in sorted(packs.glob("MBLab*.json")):
        data = json.loads(path.read_text())
        rows = {}
        for model, mesh in data["meshes"].items():
            rows[model] = {
                name: circumference(mesh["vertices"], mesh["faces"], data["height"] * height)
                for name, height in {"hips_section": .52, "waist_section": .61, "chest_section": .71}.items()
            }
        comparison = {name: {site: v - rows["ground-truth"][site]
                       if v is not None and rows["ground-truth"][site] is not None else None
                       for site, v in measures.items()}
                      for name, measures in rows.items() if name != "ground-truth"}
        result = {"closed_loop_mm": rows, "matched_section_errors_mm": comparison}
        (output / path.name).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--packs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
