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
    args = parser.parse_args()
    if args.command == "freeze-neutral":
        from .bootstrap import freeze_neutral

        try:
            print(freeze_neutral(args.assets, args.artifact_directory))
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
