# Dependency clearance

Scope: development-only installation from upstream package indexes. No third-party wheels or native binaries are redistributed by Human3D. Original code remains Apache-2.0.

| Dependency | Upstream license family | Disposition |
|---|---|---|
| NumPy | BSD-3-Clause | Development candidate; preserve notices |
| SciPy | BSD-3-Clause | Development candidate; bundled native library terms separately reviewed before distribution |
| Pillow | HPND | Development candidate; preserve notices |
| MediaPipe | Apache-2.0 | Development candidate; model assets separately cleared |
| PySide6 / Shiboken | LGPL-3.0 or GPL alternatives | Development candidate under LGPL route; no GPL-only modules admitted without review |
| OpenUSD | Modified Apache-2.0 | Development candidate; inspect upstream license and notices |

Transitive packages and bundled native libraries remain subject to individual review. Metadata alone is not clearance. No release packaging authorized until obligations, vulnerabilities, hashes and notices are recorded. Do not import MakeHuman program logic. Blender is a separate external validation application, not bundled.

## M1-007 development probe

The CPU adapter uses MediaPipe Pose Landmarker Lite float16 v1, provisioned
explicitly outside the repository. The [upstream bundle](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task)
was downloaded and verified locally as SHA-256
`59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`.
The [LiteRT community model record](https://huggingface.co/litert-community/MediaPipe-PoseLandmarker-Lite)
reports the same digest and Apache-2.0. Model redistribution remains on HOLD
under REDISTRIBUTION_CLEARANCE.md. No model files are packaged.
