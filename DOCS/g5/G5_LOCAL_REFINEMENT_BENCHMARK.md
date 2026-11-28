# G5 local refinement and native capacity

Mean symmetric closest-triangle distance in millimetres. Each reported pair uses the same subject and admitted view set. Rows marked development are exploratory. An em dash marks an unavailable result.

## A · calibrated

| Subject | Partition | D0 | L0 | D3 | D7 | D6 | D8 | D9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | held-out | 6.88 | 6.79 | 7.01 | 7.01 | 8.19 | 8.19 | 2.65 |
| A_heldout_1 | held-out | 6.37 | 6.22 | 5.17 | 5.17 | 5.74 | 5.74 | 1.13 |
| A_heldout_2 | held-out | 9.77 | 9.47 | 8.69 | 8.69 | 8.36 | 8.36 | 1.44 |
| A_high_mass | development | 3.96 | 3.94 | 2.32 | 2.32 | 3.75 | 3.75 | 0.97 |
| A_muscular | development | 5.34 | 5.34 | 4.81 | 4.81 | 5.48 | 5.90 | 3.43 |
| A_slim | held-out | 6.76 | 6.76 | 5.96 | 5.96 | 6.61 | 6.61 | 6.66 |

## B · calibrated

| Subject | Partition | D0 | L0 | D3 | D7 | D6 | D8 | D9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B_female | development | 23.12 | 23.12 | 21.11 | 21.11 | 23.79 | 23.79 | 22.59 |
| B_female_expanded | held-out | 23.19 | 23.19 | 20.90 | 20.90 | 22.94 | 22.94 | 21.09 |
| B_male | held-out | 21.13 | 21.13 | 19.91 | 17.93 | 21.10 | 21.10 | 18.56 |
| B_male_expanded | held-out | 20.85 | 20.85 | 20.40 | 18.29 | 20.12 | 20.12 | 18.58 |

## A · estimated

| Subject | Partition | D0 | L0 | D3 | D7 | D6 | D8 | D9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | held-out | 33.18 | — | 34.23 | — | 34.49 | — | 2.55 |
| A_heldout_1 | held-out | 8.83 | — | 8.82 | — | 10.22 | — | 0.00 |
| A_heldout_2 | held-out | 16.39 | — | 15.88 | — | 14.27 | — | 1.44 |
| A_high_mass | development | 10.85 | — | 8.19 | — | 6.19 | — | 0.97 |
| A_slim | held-out | 24.26 | — | 22.00 | — | 20.42 | — | 8.89 |

## B · estimated

| Subject | Partition | D0 | L0 | D3 | D7 | D6 | D8 | D9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B_female | development | 26.62 | — | 25.82 | — | 27.09 | — | 21.72 |
| B_female_expanded | held-out | 23.99 | — | 25.21 | — | 24.71 | — | 20.74 |
| B_male | held-out | 27.34 | — | 29.42 | — | 30.99 | — | 21.19 |
| B_male_expanded | held-out | 27.08 | — | 27.81 | — | 29.60 | — | 20.90 |

## Held-out subjects · calibrated impact bands

| Arm | n | Improved | Degraded | ≥5% | ≥10% | ≥20% | \|Δ\| <5% | Loss ≥5% | Best mm | Worst mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D0 | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0.00 | 0.00 |
| L0 | 7 | 3 | 0 | 0 | 0 | 0 | 7 | 0 | 0.30 | 0.00 |
| D3 | 7 | 6 | 1 | 5 | 3 | 0 | 2 | 0 | 2.29 | -0.13 |
| D7 | 7 | 6 | 1 | 6 | 5 | 0 | 1 | 0 | 3.20 | -0.13 |
| D6 | 7 | 6 | 1 | 2 | 1 | 0 | 4 | 1 | 1.42 | -1.31 |
| D8 | 7 | 6 | 1 | 2 | 1 | 0 | 4 | 1 | 1.42 | -1.31 |
| D9 | 7 | 7 | 0 | 6 | 5 | 3 | 1 | 0 | 8.33 | 0.10 |

The ≥5%, ≥10%, and ≥20% bands are nested and descriptive. Strict improvement and degradation include any signed change. Inference is paired by subject. Views contribute to the fit and never increase the independent sample count.

D7 and D8 use the same smoothed normal-direction field with a 5 mm bound. L0 uses projected contour corrections from Engine B masks. Rebind, face flips and new Blender BVH crossings are evaluated separately. Local candidates introducing new disjoint-index crossings are rejected in the reported result. The rejected proposal and the retained parent are distinguishable in the evidence. D9 measures the current registry under direct geometry. Its independent-topology optimizer is approximate ICP and therefore estimates attained capacity under a bounded schedule.

## M7 USD and Blender round trip

Accepted representatives retain topology, UV coordinates and indices, skin indices and weights relative to the same subject’s D0 export. Blender 4.5.16 imported and articulated the rig, edited a vertex, and reopened the saved scene. The archive includes the numeric verification for Family B.

| Subject | Source | Vertices | Faces | UV layers | Bones | Max skin sum error | Edit/reopen |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A_heldout_2 | A_heldout_2-D0.usd | 13380 | 13378 | 1 | 163 | 4.47e-08 | True |
| A_heldout_2 | A_heldout_2-D7.usd | 13380 | 13378 | 1 | 163 | 4.47e-08 | True |
| A_heldout_2 | A_heldout_2-D8.usd | 13380 | 13378 | 1 | 163 | 4.47e-08 | True |
| B_male | B_male-D0.usd | 13380 | 13378 | 1 | 163 | 4.47e-08 | True |
| B_male | B_male-D7.usd | 13380 | 13378 | 1 | 163 | 4.47e-08 | True |
| B_male | B_male-D8.usd | 13380 | 13378 | 1 | 163 | 4.47e-08 | True |
