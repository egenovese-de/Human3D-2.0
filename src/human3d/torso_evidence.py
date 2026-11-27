"""Consume a bounded neutral chest-to-waist section ratio."""
from collections import defaultdict

import numpy as np


def _torso_section(vertices, triangles, height):
    """Measure the largest closed contour spanning the sagittal centerline."""
    corners = np.asarray(vertices, dtype=float)[triangles]
    lower = corners[:, :, 1] <= height
    active = corners[lower.any(axis=1) & ~lower.all(axis=1)]
    edges = np.stack((active, np.roll(active, -1, axis=1)), axis=2)
    crossing = edges[(edges[:, :, 0, 1] <= height) != (edges[:, :, 1, 1] <= height)]
    if not len(crossing):
        return None
    a, b = crossing.transpose(1, 0, 2)
    points = a + ((height - a[:, 1]) / (b[:, 1] - a[:, 1]))[:, None] * (b - a)
    graph, positions = defaultdict(set), {}
    keys = list(map(tuple, np.rint(points[:, (0, 2)] * 1e7).astype(np.int64)))
    for key, point in zip(keys, points[:, (0, 2)]):
        positions[key] = point
    for a, b in zip(keys[::2], keys[1::2]):
        if a != b:
            graph[a].add(b)
            graph[b].add(a)
    unseen = set(graph)
    lengths = []
    while unseen:
        seed = unseen.pop()
        component = {seed}
        pending = [seed]
        while pending:
            for neighbor in graph[pending.pop()] & unseen:
                unseen.remove(neighbor)
                component.add(neighbor)
                pending.append(neighbor)
        if (len(component) >= 3 and all(len(graph[key]) == 2 for key in component)
                and min(key[0] for key in component) < 0 < max(key[0] for key in component)):
            lengths.append(sum(float(np.linalg.norm(positions[a] - positions[b]))
                               for a in component for b in graph[a]) / 2)
    return max(lengths, default=None)


def torso_ratio_penalty(body, evidence, aligned_keys):
    """Bound the effect of visible, mutually consistent dimensionless evidence."""
    ranges = set()
    contradictory = {key for key, reason in evidence.unresolved if reason == "inconsistent_anatomical_ratios"}
    for view in evidence.views:
        key = view.ref.photo_id
        supplied = view.detection.anatomical
        if (key not in aligned_keys or key in contradictory or supplied is None
                or supplied.candidate != view.candidate or "torso" not in view.observed_regions):
            continue
        for item in supplied.observations:
            if (item.definition != "torso.chest_to_waist_circumference@v1" or item.kind != "circumference"
                    or item.units != "ratio" or item.region != "torso" or item.frame != "subject_local"
                    or item.visibility is None or item.visibility < .8
                    or item.uncertainty is None or not 0 < item.uncertainty <= .20):
                continue
            if item.interval is None and item.value is None:
                continue
            low, high = item.interval if item.interval is not None else (item.value, item.value)
            if .6 <= low <= high <= 1.8:
                ranges.add((low - item.uncertainty, high + item.uncertainty))
    if not ranges or max(low for low, _ in ranges) > min(high for _, high in ranges):
        return None
    lo, hi = min(low for low, _ in ranges), max(high for _, high in ranges)
    mesh = body["mesh"]
    polygons = [[vertex for vertex, _ in face["corners"]] for face in mesh["faces"] if face["group"] == "body"]
    triangles = np.asarray([(face[0], face[i], face[i + 1]) for face in polygons for i in range(1, len(face) - 1)])
    if not len(triangles):
        return None
    heights = np.asarray(mesh["vertices"])[np.unique(triangles), 1]
    waist_y, chest_y = heights.min() + np.ptp(heights) * np.asarray([.61, .71])
    if not (_torso_section(mesh["vertices"], triangles, waist_y)
            and _torso_section(mesh["vertices"], triangles, chest_y)):
        return None

    def penalty(vertices):
        waist = _torso_section(vertices, triangles, waist_y)
        chest = _torso_section(vertices, triangles, chest_y)
        if not waist or not chest:
            return .02
        ratio = chest / waist
        return min(.02, .05 * max(lo - ratio, ratio - hi, 0.))

    return penalty
