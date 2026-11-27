# Controlled photographic fitting

The local score is mean symmetric surface distance in mm. Blender BVHs compare 12,000 sampled surface points in each direction using G1 seeds 818 and 819. Each model retains the same canonical frame and fixed alignment. Fits share the four-step coordinate schedule, with objective calls and elapsed times recorded per fit. Total calls vary with parameter count and bounds. The actual M6 session also has its own camera, pose, region weights, and optimizer. E0 isolates M6 controls under the matched calibrated probe, so both columns are kept.

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

E1 keeps the predicted M6 masks and calibrated IoU and changes to the G1 evaluator. E2 couples RGB border-key masks and balanced foreground/background scoring. E3 adds symmetric truncated contour distance with a small IoU term. E4 adds dense row profiles, gap and occupancy terms. The separate RGB contour+gap candidate was selected on the four original A subjects, then applied unchanged to both held-outs and Family B. E9 swaps in exact calibrated raster masks with the same G1 parameter space and dense objective. E9 is an attained comparator, so a predicted-mask fit can score better. E10 replays the prior G1 M4 solution on original references and fits the two new A subjects directly under the G1 parameter registry. The additional B fixtures have no earlier direct-geometry rows. The depth, region, correspondence and volume comparisons use matched sub-benchmarks and are excluded from the primary cumulative winner.

Mean calibrated E0/E1/G2 on the four original A cases is **37.44/4.83/4.52 mm**. On the two held-outs it is **16.87/7.32/7.30 mm**. On Family B it is **24.82/20.09/20.80 mm**. Regional height-band distances, P95/max, directional distances, cross-section errors, held-out silhouette metrics and rejected rebinds are retained in the numeric outputs. A and B are synthetic authored meshes. B has a different topology and a fixed source-to-MakeHuman stature normalization inherited from G1, with stance residuals retained.

The slim profile fails M6 rebind with `deformation_excessive_face_area_change` on contour+gap, sparse-profile and replayed E10 meshes. Its photographic fitting results remain diagnostic evidence. Its rebind guard stayed active. The editable comparison meshes are geometry scenes with source UVs and no animation rig. Production rig and pose qualification remains open.
