# Masks and negative space

### Clean MakeHuman views

| Method | Views | IoU | Dice | FP/reference | FN/reference | Boundary px | Thin recall | Gap recall | Median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M6 | 24 | 0.966 | 0.982 | 0.014 | 0.021 | 0.463 | 0.894 | 0.944 | 34.18 |
| rgb_uniform | 24 | 0.955 | 0.977 | 0.047 | 0.000 | 0.455 | 1.000 | 0.915 | 6.50 |
| M6_grabcut | 24 | 0.967 | 0.983 | 0.014 | 0.019 | 0.418 | 0.900 | 0.944 | 105.53 |

### Clean independent MB-Lab views

| Method | Views | IoU | Dice | FP/reference | FN/reference | Boundary px | Thin recall | Gap recall | Median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M6 | 16 | 0.973 | 0.986 | 0.012 | 0.015 | 0.260 | 0.911 | 0.848 | 33.26 |
| rgb_uniform | 16 | 0.954 | 0.977 | 0.048 | 0.000 | 0.432 | 1.000 | 0.722 | 6.19 |
| M6_grabcut | 16 | 0.984 | 0.992 | 0.010 | 0.007 | 0.160 | 0.959 | 0.914 | 94.67 |

### One-factor RGB stress views on the MakeHuman references

| Method | Views | IoU | Dice | FP/reference | FN/reference | Boundary px | Thin recall | Gap recall | Median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M6 | 10 | 0.961 | 0.980 | 0.015 | 0.025 | 0.355 | 0.890 | 0.990 | 33.99 |
| rgb_uniform | 10 | 0.804 | 0.860 | 0.575 | 0.000 | 4.442 | 1.000 | 0.806 | 6.43 |
| M6_grabcut | 10 | 0.968 | 0.984 | 0.022 | 0.010 | 0.304 | 0.963 | 0.984 | 116.43 |

Boundary distance is symmetric mean closest boundary distance. Thin recall is measured on foreground within 2 px of its boundary. Gap recall measures the background between occupied intervals on each row. Measurements exclude externally occluded pixels where the fixture supplies an occluder mask. The simple border key depends on a nearly uniform background. GrabCut is evaluated as a local seeded refinement, with incremental runtime reported separately from the MediaPipe prerequisite.

### Matched negative-space and mask substitutions

| Subject | M6 mask | GrabCut | RGB key | Oracle mask | M6 + explicit gap |
| --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | 6.70 | 7.02 | 6.67 | 6.91 | 4.91 |
| A_heldout_1 | 5.28 | 4.96 | 6.74 | 5.49 | 5.20 |
| A_high_mass | 2.29 | 2.31 | 2.77 | 2.27 | 2.29 |

The common loss is truncated symmetric Chamfer plus the same IoU stabilizer. The gap ablation adds only foreground occupancy in confidently empty intervals. Fit errors above are mean 3D surface error in mm. It helps primarily on the asymmetric fixture. Arms and legs make gap location strongly pose-dependent. Neck/shoulder and concave torso boundaries contribute through the contour. The evidence does not establish that tightening every gap should shrink the fitted anatomy. Explicit unknown/uncertain classes belong in the evidence representation, with high confidence required before assigning negative space.
