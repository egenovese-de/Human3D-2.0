# G6 · Registration sensitivity

| Subject | Stress or estimated arm | Parent mm | Retained mm | Gain mm | Held-out Δ IoU |
| --- | --- | --- | --- | --- | --- |
| A_heldout_1 | P_estimated_rgb_ffd | 8.83 | 12.09 | -3.26 | -0.04 |
| A_heldout_1 | P_estimated_rgb_graph | 8.83 | 8.84 | -0.01 | 0.00 |
| A_heldout_1 | P_stress_yaw_ffd | 6.37 | 6.40 | -0.03 | -0.01 |
| A_heldout_1 | P_stress_elevation_ffd | 6.37 | 4.52 | 1.85 | 0.02 |
| A_heldout_1 | P_stress_dx_ffd | 6.37 | 11.47 | -5.10 | -0.07 |
| A_heldout_1 | P_stress_span_ffd | 6.37 | 7.82 | -1.45 | -0.04 |
| A_heldout_1 | P_stress_distance_ffd | 6.37 | 4.00 | 2.37 | 0.03 |
| B_female_expanded | P_estimated_rgb_ffd | 23.99 | 25.81 | -1.83 | -0.03 |
| B_female_expanded | P_estimated_rgb_graph | 23.99 | 24.22 | -0.23 | -0.00 |
| B_female_expanded | P_stress_yaw_ffd | 23.19 | 21.01 | 2.19 | 0.03 |
| B_female_expanded | P_stress_elevation_ffd | 23.19 | 19.07 | 4.12 | 0.05 |
| B_female_expanded | P_stress_dx_ffd | 23.19 | 25.02 | -1.82 | -0.03 |
| B_female_expanded | P_stress_span_ffd | 23.19 | 21.49 | 1.70 | 0.01 |
| B_female_expanded | P_stress_distance_ffd | 23.19 | 19.28 | 3.92 | 0.05 |
| B_male | P_estimated_rgb_ffd | 27.34 | 30.10 | -2.76 | -0.05 |
| B_male | P_estimated_rgb_graph | 27.34 | 27.80 | -0.45 | -0.01 |
| B_male | P_stress_yaw_ffd | 21.13 | 18.83 | 2.30 | 0.02 |
| B_male | P_stress_elevation_ffd | 21.13 | 17.10 | 4.03 | 0.05 |
| B_male | P_stress_dx_ffd | 21.13 | 22.51 | -1.38 | -0.03 |
| B_male | P_stress_span_ffd | 21.13 | 20.08 | 1.06 | -0.00 |
| B_male | P_stress_distance_ffd | 21.13 | 17.18 | 3.95 | 0.05 |

Perturbations alter camera projection while keeping masks fixed. Yaw, elevation, translation, framing span and distance were tested. Estimated registrations reuse M7 admissible joints and poses. Explicit landmark noise, joint perturbation and scale as independently varied factors remain open. These arms use finite differences of projected contour samples and can absorb registration error into shape.
