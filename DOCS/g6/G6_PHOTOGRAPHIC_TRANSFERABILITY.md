# G6 · Photo transfer

| Subject | Arm | M7 anchor mm | Retained mm | Gain mm | Held-out Δ IoU |
| --- | --- | --- | --- | --- | --- |
| A_heldout_1 | P_oracle_1_ffd | 6.37 | 5.64 | 0.73 | 0.01 |
| A_heldout_1 | P_oracle_2_ffd | 6.37 | 3.92 | 2.45 | 0.04 |
| A_heldout_1 | P_oracle_4_ffd | 6.37 | 3.71 | 2.66 | 0.04 |
| A_heldout_1 | P_oracle_8_ffd | 6.37 | 3.43 | 2.94 | 0.05 |
| A_heldout_1 | P_calibrated_rgb_ffd | 6.37 | 4.66 | 1.71 | 0.03 |
| A_heldout_1 | P_calibrated_rgb_graph | 6.37 | 5.02 | 1.34 | 0.02 |
| A_heldout_1 | P_estimated_rgb_ffd | 8.83 | 12.09 | -3.26 | -0.04 |
| A_heldout_1 | P_estimated_rgb_graph | 8.83 | 8.84 | -0.01 | 0.00 |
| A_heldout_1 | P_stress_yaw_ffd | 6.37 | 6.40 | -0.03 | -0.01 |
| A_heldout_1 | P_stress_elevation_ffd | 6.37 | 4.52 | 1.85 | 0.02 |
| A_heldout_1 | P_stress_dx_ffd | 6.37 | 11.47 | -5.10 | -0.07 |
| A_heldout_1 | P_stress_span_ffd | 6.37 | 7.82 | -1.45 | -0.04 |
| A_heldout_1 | P_stress_distance_ffd | 6.37 | 4.00 | 2.37 | 0.03 |
| B_female_expanded | P_oracle_1_ffd | 23.19 | 20.58 | 2.61 | 0.05 |
| B_female_expanded | P_oracle_2_ffd | 23.19 | 19.19 | 4.01 | 0.05 |
| B_female_expanded | P_oracle_4_ffd | 23.19 | 18.89 | 4.30 | 0.05 |
| B_female_expanded | P_oracle_8_ffd | 23.19 | 18.05 | 5.14 | 0.06 |
| B_female_expanded | P_calibrated_rgb_ffd | 23.19 | 18.80 | 4.39 | 0.06 |
| B_female_expanded | P_calibrated_rgb_graph | 23.19 | 21.29 | 1.90 | 0.02 |
| B_female_expanded | P_estimated_rgb_ffd | 23.99 | 25.81 | -1.83 | -0.03 |
| B_female_expanded | P_estimated_rgb_graph | 23.99 | 24.22 | -0.23 | -0.00 |
| B_female_expanded | P_stress_yaw_ffd | 23.19 | 21.01 | 2.19 | 0.03 |
| B_female_expanded | P_stress_elevation_ffd | 23.19 | 19.07 | 4.12 | 0.05 |
| B_female_expanded | P_stress_dx_ffd | 23.19 | 25.02 | -1.82 | -0.03 |
| B_female_expanded | P_stress_span_ffd | 23.19 | 21.49 | 1.70 | 0.01 |
| B_female_expanded | P_stress_distance_ffd | 23.19 | 19.28 | 3.92 | 0.05 |
| B_male | P_oracle_1_ffd | 21.13 | 19.91 | 1.22 | 0.02 |
| B_male | P_oracle_2_ffd | 21.13 | 17.43 | 3.70 | 0.05 |
| B_male | P_oracle_4_ffd | 21.13 | 16.98 | 4.16 | 0.05 |
| B_male | P_oracle_8_ffd | 21.13 | 16.51 | 4.62 | 0.05 |
| B_male | P_calibrated_rgb_ffd | 21.13 | 17.20 | 3.93 | 0.05 |
| B_male | P_calibrated_rgb_graph | 21.13 | 17.75 | 3.39 | 0.04 |
| B_male | P_estimated_rgb_ffd | 27.34 | 30.10 | -2.76 | -0.05 |
| B_male | P_estimated_rgb_graph | 27.34 | 27.80 | -0.45 | -0.01 |
| B_male | P_stress_yaw_ffd | 21.13 | 18.83 | 2.30 | 0.02 |
| B_male | P_stress_elevation_ffd | 21.13 | 17.10 | 4.03 | 0.05 |
| B_male | P_stress_dx_ffd | 21.13 | 22.51 | -1.38 | -0.03 |
| B_male | P_stress_span_ffd | 21.13 | 20.08 | 1.06 | -0.00 |
| B_male | P_stress_distance_ffd | 21.13 | 17.18 | 3.95 | 0.05 |

## Existing G5 oracle-map reuse

| Subject | M7 mm | Exact depth FFD mm | Depth weighted by normal agreement mm |
| --- | --- | --- | --- |
| A_heldout_1 | 6.37 | 3.78 | 3.79 |
| B_female_expanded | 23.19 | 20.07 | 20.00 |
| B_male | 21.13 | 18.01 | 18.06 |

The RGB pipeline starts from M7 and uses bilateral contour residuals. The calibrated oracle uses exact silhouettes, camera and the known neutral pose. It does not add a stand-alone anatomical landmark objective. The oracle-depth lane uses G5 visibility, depth and optional normal agreement weights, with no new predictor. All images are synthetic authoring captures. Four held-out camera yaws provide the reprojection check. Unseen body freedom is limited by basis support, regularization and the displacement cap.
