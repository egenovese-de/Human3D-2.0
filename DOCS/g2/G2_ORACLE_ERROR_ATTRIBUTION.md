# Oracle gaps and error attribution

| Case | M6 product | E0 M6 controls | E1 G1 + M6 mask | E2 Signed | E3 Contour | E4 Dense | G2 contour + gap | E9 Photo oracle | E10 Geometry oracle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | 28.99 | 28.43 | 6.57 | 11.09 | 6.67 | 7.82 | 5.09 | 6.78 | 0.081 |
| A_heldout_1 | 11.75 | 10.47 | 5.59 | 8.90 | 6.74 | 6.59 | 5.99 | 4.91 | 0.000 |
| A_heldout_2 | 23.96 | 23.26 | 9.05 | 10.11 | 8.40 | 8.63 | 8.62 | 8.27 | 1.663 |
| A_high_mass | 17.08 | 16.84 | 2.19 | 6.37 | 2.77 | 2.93 | 3.05 | 2.12 | 0.000 |
| A_muscular | 74.63 | 73.02 | 4.68 | 8.53 | 5.14 | 4.61 | 4.98 | 4.66 | 0.000 |
| A_slim | 33.39 | 31.48 | 5.89 | 9.00 | 6.29 | 5.05 | 4.95 | 3.43 | 0.000 |
| B_female | 23.21 | 22.46 | 20.97 | 22.31 | 20.39 | 20.61 | 22.26 | 20.15 | 20.405 |
| B_female_expanded | 24.15 | 21.96 | 21.33 | 22.90 | 20.23 | 19.69 | 21.46 | 20.73 | — |
| B_male | 29.89 | 27.65 | 19.15 | 24.15 | 19.17 | 19.01 | 19.56 | 18.99 | 21.970 |
| B_male_expanded | 29.13 | 27.21 | 18.89 | 23.51 | 19.69 | 19.98 | 19.90 | 19.22 | — |

Original A G2 residual minus the attained G1 direct comparator averages **4.50 mm**. For the two same-subject G1 independent references, the analogous mean difference is **-0.28 mm**. Keep those sets and their errors separate. The direct fits quantify attained geometry with 3D supervision under their own schedules. They do not prove the representation ceiling. The photos use visibility-limited targets and a bounded derivative-free solver. Their gap includes registration, extraction, basis, stance and optimization effects. Comparing M6 product to the calibrated M6-control E0 also changes the search and loss, so it cannot isolate camera or pose. Use the controlled camera, pose, mask, landmark, depth and alternate-seed substitutions to constrain each effect.
