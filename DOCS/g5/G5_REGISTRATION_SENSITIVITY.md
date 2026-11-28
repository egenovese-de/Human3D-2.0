# G5 camera, pose and visible-surface sensitivity

Camera perturbations change the specified field while preserving the original RGB masks and truth maps. D0 here runs the G5 no-extra copy of the product schedule against deliberately corrupted registration. Distance modifies focal length and perspective depth at a fixed center span. The estimated Engine B path has separate tables.

| Control | D0 mm | D1 mm | D2 mm | D3 mm | D4 mm | D5 mm | D6 mm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| distance--110/A_high_mass | 3.38 | 4.42 | 3.17 | 2.53 | — | — | 4.08 |
| dx-0.025/A_high_mass | 7.08 | 6.64 | 10.61 | 6.38 | — | — | 8.79 |
| dy-0.025/A_high_mass | 13.92 | 12.62 | 12.90 | 12.64 | — | — | 12.75 |
| elevation-7/A_high_mass | 5.69 | 6.17 | 4.34 | 5.94 | — | — | 5.85 |
| perspective-0/A_high_mass | 3.03 | 3.23 | 3.49 | 3.53 | — | — | 4.40 |
| roll-5/A_high_mass | 5.93 | 3.49 | 3.72 | 2.78 | — | — | 5.37 |
| span-15/A_high_mass | 10.65 | 8.68 | 10.50 | 8.98 | — | — | 10.62 |
| yaw-8/A_high_mass | 6.89 | 2.53 | 3.60 | 2.85 | — | — | 4.09 |

## Pose, clothing and occlusion controls

# Controlled reference-surface changes

These are calibrated two-view oracle controls on high mass. Garment shells are procedural geometry offsets and external occlusion is a pixel exclusion control. True pose and assumed pose angles are logged for each run. This matrix isolates geometry. The separate appearance report measures RGB channel quality against exposed and covered surfaces.

| Control | D0 mm | D1 mm | D2 mm | D3 mm | D4 mm | D5 mm | D6 mm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| block_occlusion_exclude | 6.62 | — | — | 3.07 | — | — | — |
| block_occlusion_naive | 10.64 | — | — | 4.67 | — | — | — |
| close_shell_naive | 3.65 | — | — | 2.23 | — | — | — |
| loose_shell_exclude | 4.51 | — | — | 3.62 | — | — | — |
| loose_shell_naive | 4.51 | — | — | 8.53 | — | — | — |
| mild_correct | 11.10 | — | — | 2.66 | — | — | — |
| mild_error | 6.11 | — | — | 3.12 | — | — | — |
| strong_mixed_correct | 6.97 | — | — | 2.86 | — | — | — |
| strong_mixed_error | 6.65 | — | — | 4.07 | — | — | — |

## Normal-intrinsics sensitivity on estimated registrations

The main estimated table uses the synthetic RGB capture intrinsics for DSINE only. This supplementary block replaces them with the model’s 60° default and scores the same estimated M7 registration.

| Subject | Arm | Known intrinsics mm | Assumed 60° mm |
| --- | --- | --- | --- |
| A_adult_asymmetric | D5 | 33.60 | 33.43 |
| A_adult_asymmetric | D6 | 34.49 | 34.02 |
| A_heldout_1 | D5 | 9.10 | 10.65 |
| A_heldout_1 | D6 | 10.22 | 9.89 |
| A_heldout_2 | D5 | 15.60 | 16.29 |
| A_heldout_2 | D6 | 14.27 | 16.03 |
| A_high_mass | D5 | 10.05 | 8.35 |
| A_high_mass | D6 | 6.19 | 8.43 |
| A_slim | D5 | 23.76 | 22.23 |
| A_slim | D6 | 20.42 | 22.13 |
| B_female | D5 | 27.39 | 27.33 |
| B_female | D6 | 27.09 | 27.16 |
| B_female_expanded | D5 | 24.20 | 24.52 |
| B_female_expanded | D6 | 24.71 | 24.50 |
| B_male | D5 | 29.66 | 28.55 |
| B_male | D6 | 30.99 | 30.73 |
| B_male_expanded | D5 | 27.84 | 27.77 |
| B_male_expanded | D6 | 29.60 | 28.15 |
