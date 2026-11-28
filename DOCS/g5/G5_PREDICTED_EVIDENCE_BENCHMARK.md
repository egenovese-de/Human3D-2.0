# G5 pretrained evidence benchmark

Mean symmetric closest-triangle distance in millimetres. Each reported pair uses the same subject and admitted view set. Rows marked development are exploratory. An em dash marks an unavailable result.

## A · calibrated

| Subject | Partition | D0 | D4 | D5 | D6 |
| --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | held-out | 6.88 | 8.41 | 8.82 | 8.19 |
| A_heldout_1 | held-out | 6.37 | 6.11 | 5.56 | 5.74 |
| A_heldout_2 | held-out | 9.77 | 9.67 | 9.01 | 8.36 |
| A_high_mass | development | 3.96 | 4.02 | 2.87 | 3.75 |
| A_muscular | development | 5.34 | 5.19 | 5.22 | 5.48 |
| A_slim | held-out | 6.76 | 4.04 | 6.08 | 6.61 |

## B · calibrated

| Subject | Partition | D0 | D4 | D5 | D6 |
| --- | --- | --- | --- | --- | --- |
| B_female | development | 23.12 | 23.40 | 22.20 | 23.79 |
| B_female_expanded | held-out | 23.19 | 22.80 | 21.95 | 22.94 |
| B_male | held-out | 21.13 | 21.41 | 20.73 | 21.10 |
| B_male_expanded | held-out | 20.85 | 21.48 | 20.33 | 20.12 |

## A · estimated

| Subject | Partition | D0 | D4 | D5 | D6 |
| --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | held-out | 33.18 | 40.30 | 33.60 | 34.49 |
| A_heldout_1 | held-out | 8.83 | 10.26 | 9.10 | 10.22 |
| A_heldout_2 | held-out | 16.39 | 15.78 | 15.60 | 14.27 |
| A_high_mass | development | 10.85 | 8.60 | 10.05 | 6.19 |
| A_slim | held-out | 24.26 | 21.54 | 23.76 | 20.42 |

## B · estimated

| Subject | Partition | D0 | D4 | D5 | D6 |
| --- | --- | --- | --- | --- | --- |
| B_female | development | 26.62 | 25.40 | 27.39 | 27.09 |
| B_female_expanded | held-out | 23.99 | 23.70 | 24.20 | 24.71 |
| B_male | held-out | 27.34 | 29.55 | 29.66 | 30.99 |
| B_male_expanded | held-out | 27.08 | 29.45 | 27.84 | 29.60 |

## Held-out subjects · calibrated impact bands

| Arm | n | Improved | Degraded | ≥5% | ≥10% | ≥20% | \|Δ\| <5% | Loss ≥5% | Best mm | Worst mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D0 | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0.00 | 0.00 |
| D4 | 7 | 4 | 3 | 1 | 1 | 1 | 5 | 1 | 2.72 | -1.53 |
| D5 | 7 | 6 | 1 | 4 | 2 | 0 | 2 | 1 | 1.24 | -1.93 |
| D6 | 7 | 6 | 1 | 2 | 1 | 0 | 4 | 1 | 1.42 | -1.31 |

The ≥5%, ≥10%, and ≥20% bands are nested and descriptive. Strict improvement and degradation include any signed change. Inference is paired by subject. Views contribute to the fit and never increase the independent sample count.

Depth alignment during fitting uses a single D0-anchored inverse affine mapping per image. The pixel-quality report uses separate oracle-aligned validation and has a different interpretation.
