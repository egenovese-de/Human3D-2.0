"""Measure release and M6 layer validation on the same Q project inputs."""
import argparse
from hashlib import sha256
import json
import subprocess
from pathlib import Path
from time import perf_counter

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import prototype, verify_layers
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session


def revision(root):
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def cases(root):
    for identity in ("f_af01", "m_la01"):
        project = next(root.glob(f"*_{identity}_bend32-1"))
        session = Session(project / "project")
        body = load_project_body(session.store)
        neutral = deform_vertices(body, {})
        rig = body["rig"]
        view = session.shared_evidence().views[0]
        alignment = session.current_shared_fit().alignments[view.ref.photo_id]
        matrices = pose_transforms(rig, rebind_joints(rig, neutral), alignment)
        posed = skin_vertices(neutral, rig["skin"], matrices)
        top = prototype(body, neutral, "top")
        outer = prototype(body, neutral, "top", layer=1)
        shorts = prototype(body, neutral, "shorts")
        for garments in ([top, outer], [top, shorts]):
            start = perf_counter()
            result = verify_layers(garments, body, posed, matrices)
            elapsed = perf_counter() - start
            pairs = getattr(result, "pairs", ())
            yield {
                "identity": identity,
                "garments": [g.name for g in garments],
                "benchmark_sha256": sha256((project / "benchmark.json").read_bytes()).hexdigest(),
                "seconds": elapsed,
                "sampled_violations": result.violations if result else None,
                "blocked": getattr(result, "blocked", bool(result and result.violations)),
                "contacts": [{"inner": a, "outer": b, "neutral": c.neutral.__dict__,
                              "posed": c.posed.__dict__} for a, b, c in pairs],
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("product", "holdout_native", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    report = {"product_sha": revision(args.product), "lab_sha": revision(Path(__file__).parents[2]),
              "cases": list(cases(args.holdout_native))}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
