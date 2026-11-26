# Q native pipeline and ablations

Native completed runs 12/12. Fit objectives use detector evidence, while the table below uses independent evaluation masks on matched, fitted cameras and poses. An intervention may worsen a score when the native camera compensated for other errors.

| Matched evaluated silhouette IoU (%) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| matched_native | 6 | 66.518 | 66.339 | 8.563 | 57.002 | 76.800 | 56.918 |
| mask_only | 6 | 66.510 | 66.227 | 8.553 | 56.978 | 76.823 | 56.815 |
| camera_only | 6 | 66.271 | 63.639 | 6.984 | 60.195 | 75.704 | 60.154 |
| mask_and_camera | 6 | 66.251 | 63.639 | 7.013 | 60.089 | 75.711 | 60.012 |

Mask delta (percentage points) -0.01 across 6 variants (range -0.21 to +0.22). Camera delta -0.25 across 6 variants (range -3.44 to +3.24). Joint substitution delta -0.27 across 6 variants (range -3.44 to +3.09). Factorial interaction -0.01 across 6 variants (range -0.22 to +0.21).

Fixed-shape ground-truth limb-direction proxy substitution on frontal silhouettes +6.61 across 6 variants (range +4.37 to +8.71) percentage points. Model limb lengths, torso and root translation are fixed. This measures the pose output under one calibrated camera and exposes remaining anatomy/rig error. It does not measure a complete full-body oracle.

The calibrated yaw-only probe triggered the native provider conflict rule in 0/24 examined views. Partial 2D anchor replacement retains native visibility, world landmarks and unannotated landmarks. The visible native detector-to-rig-proxy RMSE averaged 7.3 px; within-view alignment effects are in the JSON. The photo-bound provider has no schema fields for an independent mesh or circumference measurements. Unsupported independent geometry cannot be passed silently through the native UV/rig contracts. Explicit omissions are recorded in the final report.
