# G6 · Free-form deformation

| Method | A held-out retained mm | B held-out proposal mm | B held-out retained mm | B paired gain mm | B backtracked |
| --- | --- | --- | --- | --- | --- |
| R2_coarse | 6.87 | 16.10 | 16.10 | 5.62 | 0/3 |
| R2_fine_budget6 | 6.61 | 13.84 | 13.84 | 7.89 | 0/3 |
| R2_fine | 6.61 | 13.42 | 13.42 | 8.30 | 0/3 |
| R2_fine_long | 6.61 | 13.34 | 13.34 | 8.38 | 0/3 |

Open tensor-product splines with 3×5×3 or 5×8×5 controls, sparse design matrix, difference regularization, robust paired correspondences and 55 mm displacement cap. Each stage caches its basis. diagnostics.json samples the Jacobian of a refit smooth field and reports how closely it embeds the retained surface. The reembedding is a diagnostic and cannot certify determinant positivity for the clipped output everywhere.
## Single-field determinant guard

The reported fine FFD uses displacement clipping and is screened against surface crossings and rig constraints. Its reembedded-field diagnostic showed nonpositive samples on some bodies, including B_female_expanded. The additional candidate fits one unclipped spline field from the M7 anchor to the retained fine-FFD result. A global displacement scale clears 3,375 sampled determinants above 0.10, then Blender performs its independent crossing screen. Samples cover the interior of the volume. They provide no continuous determinant proof.

| Subject | M7 mm | Retained guarded mm | Full-field min det | Retained min det | Combined scale |
| --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | 6.88 | 6.58 | 0.930 | 0.930 | 1.0000 |
| A_heldout_1 | 6.37 | 6.37 | 1.000 | 1.000 | 1.0000 |
| A_heldout_2 | 9.77 | 9.77 | 1.000 | 1.000 | 1.0000 |
| A_high_mass | 3.96 | 3.18 | 0.855 | 0.855 | 1.0000 |
| A_muscular | 5.34 | 3.43 | 0.825 | 0.825 | 1.0000 |
| A_slim | 6.76 | 3.79 | 0.847 | 0.847 | 1.0000 |
| B_female | 23.12 | 14.64 | 0.106 | 0.106 | 1.0000 |
| B_female_expanded | 23.19 | 14.66 | 0.597 | 0.597 | 1.0000 |
| B_male | 21.13 | 13.60 | 0.348 | 0.348 | 1.0000 |
| B_male_expanded | 20.85 | 13.47 | 0.350 | 0.350 | 1.0000 |

Independent held-out mean after determinant and surface screens is **13.91 mm**.
