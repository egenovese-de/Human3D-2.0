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
    args = parser.parse_args()
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
    if len(evidence.candidates) > 1:
        print("Multiple candidates require review before fitting.")


if __name__ == "__main__":
    main()
