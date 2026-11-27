# Confidence and multi-view evidence fusion

| Case | E4_full | camera_perturbation | alternate_seed | reverse_order | occlusion_unmasked | occlusion_oracle_state | duplicate_uniform | duplicate_only | robust_only | duplicate_robust |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_high_mass | 2.93 | 6.86 | 4.39 | 4.28 | 3.08 | 3.29 | 4.68 | 3.08 | 4.32 | 3.29 |
| A_heldout_1 | 6.59 | 9.92 | 7.40 | 4.93 | 7.14 | 6.05 | 7.78 | 7.14 | 7.54 | 6.10 |
| B_female | 20.61 | 22.80 | 21.01 | 21.71 | 20.86 | 20.50 | 20.87 | 20.86 | 20.77 | 20.33 |

Scores are mm. One deliberately corrupted frontal image replaces a clean front view. Duplicate rows add three copies of that corruption. Duplicate suppression reduces total weight to one front-view equivalent. The robust transform compresses high per-view residuals. The combined row also masks the injected occluder using an oracle annotation. Convergence traces preserve achieved objective, final error, order and initialization. Novelty is geometric and regional. A second view with a new visibility pattern may be more valuable than an exact duplicate with a high detector score.

Raw segmentation Brier scores and bin reliability, threshold sweeps, and region IoUs are in `landmark-regions.json`. Landmark confidence accompanies per-anchor residual. These scores cannot be compared directly with uncertainties in metric depth or cameras. A per-observation uncertainty needs image provenance, coordinate transform, scale and residual model. Region-specific soft weighting is preferable as a design under test. Automatic uncertainty calibration for specialized parsers, normals, dense correspondence and uncalibrated cameras remains open.
