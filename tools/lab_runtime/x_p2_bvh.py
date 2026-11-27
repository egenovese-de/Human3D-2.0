"""Check canonical-pose meshes for nonadjacent triangle intersections in Blender."""

import json
from pathlib import Path
import sys

from mathutils.bvhtree import BVHTree


def clashes(vertices, faces):
    tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    vertex_sets = [set(face) for face in faces]
    pairs = sorted({(a, b) for a, b in tree.overlap(tree)
                    if a < b and vertex_sets[a].isdisjoint(vertex_sets[b])})
    return pairs


def main(root):
    data = json.loads((root / "meshes.json").read_text())
    faces = data["triangles"]
    edge = [(0, 0, 0), (2, 0, 0), (0, 2, 0), (.3, .3, -1), (.3, .3, 1), (1, .3, 0)]
    if clashes(edge, [[0, 1, 2], [3, 4, 5]]) != [(0, 1)]:
        raise ValueError("BVH crossing control failed")
    if clashes(edge[:3] + [(0, 0, 2), (2, 0, 2), (0, 2, 2)], [[0, 1, 2], [3, 4, 5]]):
        raise ValueError("BVH separated control failed")
    meshes = {name: clashes(points, faces) for name, points in data["vertices"].items()}
    report = {}
    for name, pairs in meshes.items():
        pose = name.split("-", 1)[0]
        baseline = set(meshes[f"{pose}-neutral"])
        report[name] = {"pairs": len(pairs), "new_pairs_vs_neutral_in_pose": len(set(pairs) - baseline),
                        "intersecting_faces": len({i for pair in pairs for i in pair}),
                        "face_pairs": pairs}
    (root / "intersections.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"X_P2_BVH_PASS {len(report)} meshes")


if __name__ == "__main__":
    main(Path(sys.argv[sys.argv.index("--") + 1]))
