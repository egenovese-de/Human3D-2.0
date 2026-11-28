# G5 exact evidence benchmark

Mean symmetric closest-triangle distance in millimetres. Each reported pair uses the same subject and admitted view set. Rows marked development are exploratory. An em dash marks an unavailable result.

## A · calibrated

| Subject | Partition | D0 | D1 | D2 | D3 | D9 |
| --- | --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | held-out | 6.88 | 6.86 | 6.34 | 7.01 | 2.65 |
| A_heldout_1 | held-out | 6.37 | 5.55 | 6.13 | 5.17 | 1.13 |
| A_heldout_2 | held-out | 9.77 | 9.05 | 8.96 | 8.69 | 1.44 |
| A_high_mass | development | 3.96 | 2.28 | 2.41 | 2.32 | 0.97 |
| A_muscular | development | 5.34 | 4.89 | 4.93 | 4.81 | 3.43 |
| A_slim | held-out | 6.76 | 3.62 | 7.19 | 5.96 | 6.66 |

## B · calibrated

| Subject | Partition | D0 | D1 | D2 | D3 | D9 |
| --- | --- | --- | --- | --- | --- | --- |
| B_female | development | 23.12 | 21.96 | 21.86 | 21.11 | 22.59 |
| B_female_expanded | held-out | 23.19 | 21.00 | 21.94 | 20.90 | 21.09 |
| B_male | held-out | 21.13 | 20.38 | 20.01 | 19.91 | 18.56 |
| B_male_expanded | held-out | 20.85 | 19.46 | 21.16 | 20.40 | 18.58 |

## A · estimated

| Subject | Partition | D0 | D1 | D2 | D3 | D9 |
| --- | --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | held-out | 33.18 | 39.18 | 33.71 | 34.23 | 2.55 |
| A_heldout_1 | held-out | 8.83 | 11.28 | 9.45 | 8.82 | 0.00 |
| A_heldout_2 | held-out | 16.39 | 14.21 | 16.02 | 15.88 | 1.44 |
| A_high_mass | development | 10.85 | 6.99 | 10.74 | 8.19 | 0.97 |
| A_slim | held-out | 24.26 | 18.48 | 22.65 | 22.00 | 8.89 |

## B · estimated

| Subject | Partition | D0 | D1 | D2 | D3 | D9 |
| --- | --- | --- | --- | --- | --- | --- |
| B_female | development | 26.62 | 25.78 | 25.22 | 25.82 | 21.72 |
| B_female_expanded | held-out | 23.99 | 24.07 | 26.16 | 25.21 | 20.74 |
| B_male | held-out | 27.34 | 30.71 | 28.41 | 29.42 | 21.19 |
| B_male_expanded | held-out | 27.08 | 28.32 | 28.05 | 27.81 | 20.90 |

## Held-out subjects · calibrated impact bands

| Arm | n | Improved | Degraded | ≥5% | ≥10% | ≥20% | \|Δ\| <5% | Loss ≥5% | Best mm | Worst mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D0 | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0.00 | 0.00 |
| D1 | 7 | 7 | 0 | 5 | 2 | 1 | 2 | 0 | 3.14 | 0.02 |
| D2 | 7 | 5 | 2 | 4 | 0 | 0 | 2 | 1 | 1.26 | -0.43 |
| D3 | 7 | 6 | 1 | 5 | 3 | 0 | 2 | 0 | 2.29 | -0.13 |
| D9 | 7 | 7 | 0 | 6 | 5 | 3 | 1 | 0 | 8.33 | 0.10 |

The ≥5%, ≥10%, and ≥20% bands are nested and descriptive. Strict improvement and degradation include any signed change. Inference is paired by subject. Views contribute to the fit and never increase the independent sample count.
