# Q multi-view scaling

| Configuration, held-out silhouette IoU (%) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| bootstrap | 6 | 71.041 | 70.658 | 2.964 | 67.484 | 74.740 | 66.867 |
| front | 6 | 71.886 | 71.719 | 3.288 | 67.771 | 75.695 | 67.113 |
| front-profile | 6 | 72.415 | 72.433 | 3.159 | 68.357 | 75.952 | 67.705 |
| front-rear | 6 | 71.886 | 71.719 | 3.288 | 67.771 | 75.695 | 67.113 |
| three | 6 | 72.368 | 72.376 | 3.238 | 68.265 | 76.029 | 67.674 |
| four | 6 | 72.412 | 72.390 | 3.156 | 68.384 | 75.978 | 67.742 |
| eight | 6 | 72.438 | 72.481 | 3.146 | 68.425 | 75.982 | 67.836 |
| direct_coarse | 6 | 71.203 | 71.495 | 3.137 | 67.191 | 74.780 | 66.731 |
| direct_refined | 6 | 71.227 | 71.478 | 3.197 | 67.162 | 74.880 | 66.707 |
| native_1 | 6 | 70.827 | 71.258 | 3.723 | 66.319 | 74.755 | 66.157 |
| native_4 | 6 | 69.918 | 70.085 | 3.293 | 65.988 | 73.854 | 65.694 |

| Calibrated fit wall time (s) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| front | 6 | 46.587 | 51.092 | 15.172 | 25.356 | 59.695 | 21.451 |
| front-profile | 6 | 49.029 | 45.215 | 15.984 | 36.059 | 72.259 | 34.773 |
| front-rear | 6 | 48.288 | 40.084 | 20.653 | 34.460 | 79.112 | 33.313 |
| three | 6 | 65.419 | 59.408 | 23.548 | 45.575 | 99.365 | 42.156 |
| four | 6 | 68.787 | 63.458 | 14.918 | 59.114 | 90.629 | 57.868 |
| eight | 6 | 109.433 | 106.699 | 11.247 | 98.953 | 124.416 | 98.529 |
| direct_coarse | 6 | 15.986 | 16.730 | 4.473 | 9.774 | 20.559 | 8.186 |
| direct_refined | 6 | 41.115 | 38.590 | 12.408 | 29.476 | 58.924 | 28.663 |

Paired held-out effects versus one frontal calibrated photograph, in percentage points.

- front-profile +0.53 across 6 variants (range +0.22 to +0.83)
- front-rear +0.00 across 6 variants (range +0.00 to +0.00)
- three +0.48 across 6 variants (range +0.29 to +0.78)
- four +0.53 across 6 variants (range +0.26 to +0.80)
- eight +0.55 across 6 variants (range +0.27 to +0.89)

The two-view front/profile and front/rear treatments differ solely in the second orientation. Four includes both profiles, eight includes 45-degree increments. Held-out values average two unused cameras per variant. Native one/four rows report neutral shapes under the same held-out cameras and fixed alignment. Their detector-mask training scores cannot be compared directly with controlled IoU. Runtime includes concurrent scheduling noise. Contradictory and different-pose cases remain open. The supplementary repeat applies an identical short 128 px coordinate pass to each configuration and includes a deliberately duplicated front image. Neither held-out angle is used among the sixteen inputs.

| Supplementary held-out IoU (%) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| three | 2 | 73.641 | 73.641 | 3.013 | 71.724 | 75.559 | 71.511 |
| four | 2 | 73.598 | 73.598 | 3.074 | 71.641 | 75.554 | 71.424 |
| eight | 2 | 73.691 | 73.691 | 3.193 | 71.660 | 75.723 | 71.434 |
| eight_repeat | 2 | 73.691 | 73.691 | 3.193 | 71.660 | 75.723 | 71.434 |
| sixteen | 2 | 73.764 | 73.764 | 3.036 | 71.832 | 75.696 | 71.618 |
| duplicate_front | 2 | 73.641 | 73.641 | 3.013 | 71.724 | 75.559 | 71.511 |

- MBLab_human_female_base eight-view repeat matched controls and IoU: True. Wall times 36.25 s and 32.25 s.
- MBLab_human_male_base eight-view repeat matched controls and IoU: True. Wall times 35.34 s and 31.39 s.
