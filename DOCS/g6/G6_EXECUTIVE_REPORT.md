# G6 · Executive decision

**Recommendation B. Qualify native initialization plus bounded volumetric FFD as the next candidate.** Keep M7 as the production fallback. Enable no advanced deformation for estimated registration based on these results. This is partial experimental qualification.

The actual qualified M7 branch ran on all 10 calibrated references. Estimated registration produced 9/10 complete results. The direct G5 benchmark was rerun with its original implementation, seeded from the fresh M7 outputs. Blender nearest-triangle evaluation preserved the G5 sampling convention.

| Method | A held-out retained mm | B held-out proposal mm | B held-out retained mm | B paired gain mm | B backtracked |
| --- | --- | --- | --- | --- | --- |
| D0 | 7.45 | 21.73 | 21.73 | 0.00 | 0/3 |
| R0_D9 | 2.97 | 19.41 | 19.41 | 2.32 | 0/3 |
| R0_long | 2.88 | 20.16 | 20.16 | 1.56 | 0/3 |
| R0_restart | 2.60 | 18.64 | 18.64 | 3.08 | 0/3 |
| R1_extended | 7.35 | 19.03 | 19.03 | 2.69 | 0/3 |
| R2_coarse | 6.87 | 16.10 | 16.10 | 5.62 | 0/3 |
| R2_fine | 6.61 | 13.42 | 13.42 | 8.30 | 0/3 |
| R2_fine_long | 6.61 | 13.34 | 13.34 | 8.38 | 0/3 |
| R3_cage | 6.70 | 19.38 | 19.38 | 2.35 | 0/3 |
| R4_graph48 | 7.29 | 14.85 | 20.41 | 1.32 | 3/3 |
| R4_graph120 | 7.28 | 19.16 | 20.37 | 1.35 | 3/3 |
| R5_symmetric | 7.36 | 17.37 | 21.44 | 0.28 | 3/3 |
| R6_lattice | 6.61 | 10.95 | 17.07 | 4.65 | 3/3 |
| R6_graph | 7.28 | 17.01 | 21.19 | 0.53 | 3/3 |

The fine spline lattice at 14 iterations lowers independent held-out mean error from **21.73 to 13.42 mm**, an **38.2%** paired reduction over M7 across three independent bodies. The 28-step ceiling probe reached **13.34 mm**. The strongest proposal by mean was the fine lattice followed by per-vertex refinement at **10.95 mm**. Screening brought that result to **17.07 mm**. Select the simpler fine lattice.

## Photographic transfer

| Subject | Arm | M7 anchor mm | Retained mm | Gain mm | Held-out Δ IoU |
| --- | --- | --- | --- | --- | --- |
| A_heldout_1 | P_oracle_4_ffd | 6.37 | 3.71 | 2.66 | 0.04 |
| A_heldout_1 | P_calibrated_rgb_ffd | 6.37 | 4.66 | 1.71 | 0.03 |
| A_heldout_1 | P_estimated_rgb_ffd | 8.83 | 12.09 | -3.26 | -0.04 |
| B_female_expanded | P_oracle_4_ffd | 23.19 | 18.89 | 4.30 | 0.05 |
| B_female_expanded | P_calibrated_rgb_ffd | 23.19 | 18.80 | 4.39 | 0.06 |
| B_female_expanded | P_estimated_rgb_ffd | 23.99 | 25.81 | -1.83 | -0.03 |
| B_male | P_oracle_4_ffd | 21.13 | 16.98 | 4.16 | 0.05 |
| B_male | P_calibrated_rgb_ffd | 21.13 | 17.20 | 3.93 | 0.05 |
| B_male | P_estimated_rgb_ffd | 27.34 | 30.10 | -2.76 | -0.05 |

Calibrated RGB results use the actual M7 masks, known camera and canonical observation pose. Estimated results use admitted M7 poses and cameras. This is synthetic RGB capture with ground-truth geometry available for evaluation. The estimated lane uses first-order contour Jacobians that do not differentiate rebinding and articulation. The strongest observed estimate-lane regression in the tested candidates was **3.26 mm** on A_heldout_1 with P_estimated_rgb_ffd.

## Qualification and release implications

- Existing-family optimizer restart reached **18.64 mm** versus **19.41 mm** with the re-executed G5 direct oracle. Shoulder and arm stance materially alter the measured residual. Simultaneous limb orientation transfer regressed.
- The full fine FFD candidates on the three independent held-outs cleared the no-new-crossings rule against M7. Blender 4.5.16 qualified 4 USD round trips across one representative from each family. The controlled native pose screen measured 980 retained/rebound checks with 0 product pose-validator failures. Collision evidence is separate.
- G5 predictor integration remains deferred. Exact depth improves isolated FFD tests. The normal-consistency weights provide mixed incremental effect. These are existing exact-map oracle controls. No new predictor or learned evidence was qualified.
- The target Windows 11 workstation and real capture benchmark remain open. Windows CI covers the small CPU geometry-operator subset. The technical decision is conditional on registration, full rig and export validation, and real capture evidence.

Use the decision matrix and the reproduction instructions to plan the gated M9 study. The canonical topology remains the branch’s reference contract. Fine anatomical detail and topology redesign require separate evidence and product decisions.
## Determinant and CI disposition

The fine FFD surface benchmark remains **13.42 mm**. A separate single spline field with a sampled determinant guard and crossing check retains **13.91 mm** on the same three independent held-out subjects. This identifies a concrete stability cost to carry into M9. The selected architecture needs direct coefficient bounds and conservative determinant validation before enabling end-user volume deformation.

The qualified M7 revision is `020fcc793e7417d6927d9e07346678e110ae9ddc`. The CPU operator subset passed on Linux and Windows Server in CI on experimental revision `d18f15bb3a9208cb8c31030d09fd7c9b4e50eb84`. The local experiment artifacts carry full-matrix fit and validation logs.

[Representative CI run](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46149317774) · [G6 branch](https://github.com/egenovese-de/Human3D-2.0/tree/lab/g6-geometry-capacity)
