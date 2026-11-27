"""Record exact garment contact regions without redistributing source geometry."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from audit_bind_frames import revision
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import (_body_faces, _triangulate, correct_clearance, posed_garment,
                              prototype, repair_garment_contacts)
from human3d.native_rig import pose_transforms, skin_vertices, validate_rebind
from human3d.session import Session
from human3d.triangle_collision import triangle_contact_pairs


def contact_records(obstacle_points, obstacle_faces, shell_points, shell_faces, skin):
    obstacle = np.asarray(obstacle_points)[obstacle_faces]
    triangles = shell_points[shell_faces]
    pairs = [{"obstacle_face": i, "shell_face": j, "kind": kind,
              "center_dm": triangles[j].mean(0).tolist(),
              "dominant_bones": sorted({max(skin[k], key=skin[k].get) for k in shell_faces[j]})}
             for i, j, kind in triangle_contact_pairs(obstacle, triangles) if kind != "touching"]
    hits = {pair["shell_face"] for pair in pairs}
    adjacency = defaultdict(set)
    for face in hits:
        for vertex in shell_faces[face]:
            adjacency[int(vertex)].add(face)
    regions = []
    while hits:
        seed = min(hits)
        connected = {seed}
        hits.remove(seed)
        pending = [seed]
        while pending:
            face = pending.pop()
            neighbors = set().union(*(adjacency[int(vertex)] for vertex in shell_faces[face]))
            for neighbor in sorted(neighbors & hits):
                connected.add(neighbor)
                pending.append(neighbor)
                hits.remove(neighbor)
        regions.append(sorted(connected))
    return {"pairs": pairs, "connected_shell_regions": regions}


def run(candidate, project, output, ease):
    session = Session(project)
    fit = session.current_shared_fit()
    body = load_project_body(session.store)
    rig = body["rig"]
    target = session.store.load().photos.target
    neutral = deform_vertices(body, fit.fit.controls)
    transforms = pose_transforms(rig, validate_rebind(body, neutral), fit.alignments[target])
    posed = skin_vertices(neutral, rig["skin"], transforms)
    garment, sampled = correct_clearance(prototype(body, neutral, "top", ease_mm=ease), body, posed, transforms)
    body_faces = _triangulate(_body_faces(body))
    shell_faces = _triangulate(garment.faces)

    def stages(shell):
        return {"neutral": contact_records(neutral, body_faces, shell.points, shell_faces, shell.skin),
                "posed": contact_records(posed, body_faces, posed_garment(shell, transforms), shell_faces, shell.skin)}

    start = perf_counter()
    repaired = repair_garment_contacts(garment, body, neutral, posed, transforms)
    seconds = perf_counter() - start
    result = {"candidate_sha": revision(candidate), "lab_sha": revision(Path(__file__).parents[2]),
              "fixture": project.parent.name, "ease_mm": ease, "sampled_violations": sampled.violations,
              "input_benchmark_sha256": sha256((project.parent / "benchmark.json").read_bytes()).hexdigest(),
              "repair_seconds": seconds, "repair_accepted": repaired is not garment,
              "peak_rest_displacement_mm": float(np.linalg.norm(repaired.points - garment.points, axis=1).max() * 100),
              "before": stages(garment), "after": stages(repaired)}
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "project", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--ease", type=float, default=6)
    run(**vars(parser.parse_args()))
