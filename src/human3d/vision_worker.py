"""Subprocess entry point for native subject detection."""
import argparse
from pathlib import Path

from .observations import ObservationStore
from .vision import _NativePoseLandmarker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("original", type=Path)
    parser.add_argument("digest")
    parser.add_argument("output", type=Path)
    parser.add_argument("--segmentation", action="store_true")
    args = parser.parse_args()

    detector = _NativePoseLandmarker(args.model, segmentation=args.segmentation)
    try:
        evidence = detector.detect(args.original, args.digest)
    except ValueError as error:
        print(str(error))
        return 1
    finally:
        detector.close()
    print(ObservationStore(args.output).write_detection(evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
