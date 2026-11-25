"""Run the native product path on a locally supplied synthetic fixture manifest."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
from time import perf_counter

from PIL import Image

from human3d.appearance import prepare_view
from human3d.bootstrap import freeze_project
from human3d.fitting import _scorer
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.originals import OriginalStore
from human3d.session import Session
from human3d.texture_bake import bake_atlas
from human3d.usd_export import export_body
from human3d.vision import PoseLandmarker


def revision(root):
    if subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True).strip():
        raise ValueError(f"Commit benchmark sources before running: {root}")
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def fixtures(manifest):
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for row in data.get("images", data.get("files", [])):
        path = manifest.parent / row["file"]
        if sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError(f"fixture_digest_mismatch: {path.name}")
        with Image.open(path) as image:
            image.verify()
        yield path, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("product", "manifest", "assets", "model", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--target")
    args = parser.parse_args()
    import human3d
    if Path(human3d.__file__).resolve().parents[2] != args.product.resolve():
        raise ValueError("Set PYTHONPATH to the product checkout's src directory.")
    report = {"product_sha": revision(args.product), "lab_sha": revision(Path(__file__).parents[1]),
              "python": platform.python_version(), "platform": platform.platform(), "detections": {}}
    args.output.mkdir(parents=True, exist_ok=False)
    report_path = args.output / "benchmark.json"
    cases = list(fixtures(args.manifest))
    session = Session(args.output / "project", create=True)
    detector = PoseLandmarker(args.model, segmentation=True)
    try:
        if args.target:
            session.ingest([path for path, _ in cases])
            photo_ids = {photo.digest: photo.id for photo in session.store.load().photos.photos}
        for path, row in cases:
            digest = row["sha256"]
            started = perf_counter()
            evidence = (session.detect_photo(photo_ids[digest], detector) if args.target
                        else detector.detect(path, digest))
            report["detections"][path.name] = {
                "sha256": digest, "image_size": evidence.image_size,
                "candidates": len(evidence.candidates), "reason": evidence.review_reason,
                "masks": sum(mask is not None for mask in evidence.masks),
                "seconds": perf_counter() - started,
            }
        if not args.target:
            return

        target = photo_ids[next(row["sha256"] for path, row in cases if path.name == args.target)]
        session.select_target(target)
        freeze_digest = freeze_project(session.store, args.assets)
        report["frozen_sha256"] = freeze_digest
        started = perf_counter()
        shared = session.fit_shared()
        report["fit_seconds"] = perf_counter() - started
        report["fit"] = {"controls": shared.fit.controls, "bootstrap_iou": shared.fit.bootstrap_iou,
                         "fitted_iou": shared.fit.fitted_iou, "per_view_iou": shared.scores,
                         "saturated": sorted(name for name, value in shared.fit.controls.items() if abs(value) == .5)}
        body = load_project_body(session.store)
        evidence = session.shared_evidence()
        masks = {view.ref.photo_id: view.mask for view in evidence.views if view.ref.photo_id in shared.scores}
        neutral = deform_vertices(body, {})
        fitted = deform_vertices(body, shared.fit.controls)
        score = _scorer(body, masks, shared.alignments, neutral)
        report["fixed_camera_pose"] = {"bootstrap": score(neutral), "fitted": score(fitted)}
        originals = OriginalStore(session.store.directory)
        views = {view.ref.photo_id: (
            prepare_view(originals, view, shared.alignments[view.ref.photo_id]), view.detection.image_size
        ) for view in evidence.views if view.ref.photo_id in shared.scores}
        alignment = shared.alignments[target]
        export_body(args.output / "native.usdc", body, shared.fit, alignment)
        atlas = bake_atlas(body, shared.fit.controls, views, target)
        report["observed_uv_fraction"] = atlas.observed_fraction
        export_body(args.output / "native.usdz", body, shared.fit, alignment, texture=atlas.color)
    except Exception as error:
        report["error"] = type(error).__name__
        raise
    finally:
        detector.close()
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
