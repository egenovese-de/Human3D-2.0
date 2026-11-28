"""Extract the G2 masks for one locally rendered MakeHuman control."""
from pathlib import Path
import sys
import cv2

from g1_benchmark import Engine
from human3d.vision import _NativePoseLandmarker
from photographic import calibration
from projection import Raster


def main(reference, rgb, model, raster, output):
    cv2.setNumThreads(1)
    detector=_NativePoseLandmarker(model,segmentation=True)
    calibration(reference.stem,reference,rgb,output/'evidence_maps'/reference.stem,
                detector,Engine(),Raster(raster))
    detector.close()


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
