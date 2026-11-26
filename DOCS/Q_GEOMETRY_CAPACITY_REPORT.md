# Q geometry capacity

6 completed independent variant evaluations. Each estimate is conditional on the rig family, rest stance and common height/floor alignment. Error mixes morphology and residual rest-stance mismatch.

| Symmetric sampled surface error, height-aligned mm | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| bootstrap | 6 | 35.947 | 36.359 | 8.014 | 26.598 | 46.114 | 25.662 |
| front | 6 | 34.248 | 33.857 | 8.201 | 25.301 | 45.195 | 24.725 |
| front-profile | 6 | 33.692 | 33.036 | 8.085 | 25.114 | 44.584 | 24.703 |
| front-rear | 6 | 34.248 | 33.857 | 8.201 | 25.301 | 45.195 | 24.725 |
| three | 6 | 33.754 | 33.164 | 8.182 | 25.036 | 44.750 | 24.622 |
| four | 6 | 33.670 | 33.018 | 8.144 | 24.990 | 44.633 | 24.537 |
| eight | 6 | 33.758 | 33.183 | 8.063 | 25.070 | 44.511 | 24.630 |
| direct_coarse | 6 | 34.838 | 34.146 | 8.037 | 25.954 | 45.638 | 25.012 |
| direct_refined | 6 | 34.821 | 34.167 | 8.022 | 25.964 | 45.571 | 25.103 |
| native_1 | 6 | 34.599 | 34.624 | 7.932 | 26.034 | 44.967 | 25.904 |
| native_4 | 6 | 35.247 | 34.917 | 8.131 | 26.704 | 46.122 | 26.548 |

The JSON contains region means, Chamfer, P95 error, fitted controls and saturation. All native runs used the identical frozen MakeHuman base digest. The automatic search has circumference, length and regional controls and lacks a separate base anatomy selector. The male case exposes a persistent chest-profile mismatch under the measured basis. Height and first-visible surface validation are independent of the release. Section metrics report hip, waist and chest closed-loop circumferences in height-aligned millimeters. Empty contours are retained as missing. Shoulder/hip span ratios use paired bone-anchor proxies. Volumetric IoU estimates use three-axis majority ray parity on a fixed cubic grid. MB-Lab surface boundaries make occupancy approximate, and the JSON retains ambiguous voxels and boundary edge counts. Registered vertex RMSE is unavailable for independent topologies. Fixed-band held-out IoU is reported for cranium, torso/arms and lower body. The historical seeded sensitivity run recovered control displacement and saturation within the same basis. Direct-fit step refinement measures optimizer sensitivity conditional on its nearest-sample objective. A persistent residual after the direct search is evidence of a limitation under the tested rest alignment and basis; the pilot cannot uniquely attribute it to geometry capacity.

| Approximate height-aligned volumetric IoU (%) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| native | 6 | 59.279 | 60.672 | 10.592 | 45.516 | 70.342 | 44.039 |
| calibrated-four | 6 | 60.755 | 62.495 | 10.195 | 47.277 | 71.535 | 45.707 |
| direct-3d | 6 | 58.833 | 60.424 | 10.420 | 45.204 | 70.453 | 43.554 |
