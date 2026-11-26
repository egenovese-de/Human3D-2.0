# Q photographic robustness

Measured 132 detector calls. Mask statistics use available detector masks and include low-visibility cases. Missing masks are counted in the separate detector totals.

| Perturbation, mask IoU (%) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| yaw 0 | 6 | 96.979 | 97.135 | 0.351 | 96.532 | 97.263 | 96.525 |
| yaw 90 | 6 | 97.965 | 97.984 | 0.227 | 97.668 | 98.206 | 97.598 |
| yaw 180 | 6 | 97.058 | 97.090 | 0.303 | 96.680 | 97.382 | 96.622 |
| yaw 270 | 6 | 97.958 | 98.057 | 0.285 | 97.570 | 98.198 | 97.517 |
| yaw 45 | 6 | 97.158 | 97.214 | 0.220 | 96.839 | 97.348 | 96.740 |
| yaw 135 | 6 | 97.433 | 97.476 | 0.274 | 97.100 | 97.739 | 97.076 |
| yaw 225 | 6 | 97.293 | 97.264 | 0.109 | 97.169 | 97.430 | 97.144 |
| yaw 315 | 6 | 97.414 | 97.374 | 0.126 | 97.291 | 97.593 | 97.269 |
| resolution | 6 | 93.990 | 93.933 | 0.720 | 93.157 | 94.869 | 93.082 |
| jpeg | 6 | 90.678 | 90.427 | 0.570 | 90.213 | 91.479 | 90.209 |
| noise | 6 | 94.480 | 95.282 | 1.902 | 91.818 | 96.151 | 91.513 |
| dark | 6 | 96.385 | 96.957 | 1.002 | 94.964 | 97.090 | 94.810 |
| crop | 6 | 97.462 | 97.419 | 0.150 | 97.333 | 97.682 | 97.325 |
| occlusion | 6 | 91.027 | 91.287 | 3.571 | 86.833 | 94.537 | 86.398 |
| clutter | 6 | 94.437 | 94.548 | 0.559 | 93.662 | 95.000 | 93.526 |
| illumination-gradient | 6 | 97.144 | 97.071 | 0.178 | 96.987 | 97.382 | 96.981 |
| wide-perspective | 6 | 97.052 | 97.072 | 0.121 | 96.910 | 97.178 | 96.910 |
| long-perspective | 6 | 97.124 | 97.133 | 0.195 | 96.869 | 97.334 | 96.822 |
| elevated | 6 | 97.117 | 97.072 | 0.329 | 96.701 | 97.478 | 96.597 |
| low | 6 | 97.254 | 97.249 | 0.154 | 97.073 | 97.452 | 97.036 |

| Perturbation | Calls | Single candidate | Review or error |
|---|---:|---:|---:|
| yaw 0 | 6 | 6 | 0 |
| yaw 90 | 6 | 6 | 6 |
| yaw 180 | 6 | 6 | 0 |
| yaw 270 | 6 | 6 | 6 |
| yaw 45 | 6 | 6 | 0 |
| yaw 135 | 6 | 6 | 4 |
| yaw 225 | 6 | 6 | 2 |
| yaw 315 | 6 | 6 | 0 |
| resolution | 6 | 6 | 0 |
| jpeg | 6 | 6 | 0 |
| blur | 6 | 0 | 6 |
| noise | 6 | 6 | 0 |
| dark | 6 | 6 | 0 |
| crop | 6 | 6 | 1 |
| occlusion | 6 | 6 | 0 |
| clutter | 6 | 6 | 0 |
| illumination-gradient | 6 | 6 | 0 |
| compound | 6 | 0 | 6 |
| wide-perspective | 6 | 6 | 0 |
| long-perspective | 6 | 6 | 0 |
| elevated | 6 | 6 | 0 |
| low | 6 | 6 | 0 |

The perspective rows vary focal length, camera distance and elevation with known Blender matrices. This arm measures detector segmentation robustness, without attributing improvements to camera reconstruction. The clutter and illumination gradient are deterministic pixel transforms. Crop and occlusion are measured against their documented mask conventions. Extra stress photographs are available only as local regenerable artifacts.

Both photorealistic AI inputs produced a usable one-person run and exported a top. Candidate garment overlaps were 83.09% and 79.04% against native appearance-derived coverage. These results are qualitative for 3D accuracy, including generated clothing and backgrounds. They do not establish independent mask IoU or garment shape accuracy.
