"""Human3D command line entry point."""
import argparse
from pathlib import Path

from . import __version__


def main():
    parser = argparse.ArgumentParser(description="Human3D 2.0")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    detection = commands.add_parser("detect-target", help="Inspect subject candidates in a saved project's target")
    detection.add_argument("project", type=Path)
    detection.add_argument("--model", type=Path, required=True, help="Local Pose Landmarker Lite v1 bundle")
    freeze = commands.add_parser("freeze-neutral", help="Freeze a verified neutral mesh and rig")
    freeze.add_argument("assets", type=Path)
    freeze.add_argument("artifact_directory", type=Path)
    freeze.add_argument("--with-morphs", action="store_true", help="Embed the eight verified MORPH-02 targets")
    project_freeze = commands.add_parser("freeze-project", help="Attach a frozen rest body to a saved project")
    project_freeze.add_argument("project", type=Path)
    project_freeze.add_argument("--assets", type=Path, required=True)
    inspection = commands.add_parser("inspect-body", help="Inspect the project's native rest body")
    inspection.add_argument("project", type=Path)
    args = parser.parse_args()
    if args.command in {"freeze-project", "inspect-body"}:
        from .project_store import ProjectStore

        store = ProjectStore(args.project)
        try:
            if args.command == "freeze-project":
                from .bootstrap import freeze_project

                print(freeze_project(store, args.assets))
            else:
                from .frozen_body import load_project_body

                body = load_project_body(store)
                mesh = body["mesh"]
                print(f"Vertices: {len(mesh['vertices'])}, faces: {len(mesh['faces'])}, "
                      f"bones: {len(body['rig']['bones'])}, morph targets: {len(body.get('morph_targets', {}))}")
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            parser.exit(1, f"Frozen body operation failed: {error}\n")
        return
    if args.command == "freeze-neutral":
        from .bootstrap import freeze_neutral

        try:
            print(freeze_neutral(args.assets, args.artifact_directory, with_morphs=args.with_morphs))
        except (OSError, ValueError) as error:
            parser.exit(1, f"Freeze failed: {error}\n")
        return
    if args.command != "detect-target":
        return

    from .session import Session
    from .vision import PoseLandmarker

    try:
        session = Session(args.project)
        detector = PoseLandmarker(args.model)
        try:
            evidence = session.detect_target(detector)
        finally:
            detector.close()
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f"Detection failed: {error}\n")
    if evidence is None:
        parser.exit(1, "Evidence was discarded. Run again on the current target.\n")
    if not evidence.candidates:
        parser.exit(1, "No subject detected. Select another photo and retry.\n")
    print(f"Subject candidates: {len(evidence.candidates)}")
    if evidence.review_reason:
        parser.exit(1, f"Subject review required ({evidence.review_reason}). Select another photo and retry.\n")


if __name__ == "__main__":
    main()
