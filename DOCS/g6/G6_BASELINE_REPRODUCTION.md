# G6 · Historical baseline reproduction

| Subject | G5 D0 mm | G6 M7 D0 mm | G5 D9 mm | G6 replay D9 mm |
| --- | --- | --- | --- | --- |
| A_adult_asymmetric | 6.88 | 6.88 | 2.65 | 2.65 |
| A_heldout_1 | 6.37 | 6.37 | 1.13 | 1.13 |
| A_heldout_2 | 9.77 | 9.77 | 1.44 | 1.44 |
| A_high_mass | 3.96 | 3.96 | 0.97 | 0.97 |
| A_muscular | 5.34 | 5.34 | 3.43 | 3.43 |
| A_slim | 6.76 | 6.76 | 6.66 | 6.66 |
| B_female | 23.12 | 23.12 | 22.59 | 22.59 |
| B_female_expanded | 23.19 | 23.19 | 21.09 | 21.09 |
| B_male | 21.13 | 21.13 | 18.56 | 18.56 |
| B_male_expanded | 20.85 | 20.85 | 18.58 | 18.58 |

The service uses M7 Engine B through Session and ReconstructionService. Family A reuses the original RGB bytes. Family B renders from verified local references with the pinned G5 script. R0_D9 reuses G5 direct_fit. L0 was rerun for three photo subjects with G5 refine and measured separately. See the original G5 D7/D8 for full exact/learned local comparisons. Numerical comparisons use the same metric and units.
## Numeric reconciliation

Maximum absolute G5-to-G6 differences are 0.000000 mm for D0 and 0.000000 mm for D9. L0 replay below shows the numeric proposal and new crossings. G5 retained D0 when its L0 crossing rule rejected the proposal. Refer to the structural policy before comparing these columns.

| Subject | G5 retained L0 mm | G6 L0 replay proposal mm | New crossings |
| --- | --- | --- | --- |
| A_heldout_1 | 6.222 | 6.222 | 0 |
| B_male | 21.132 | 21.132 | 0 |
| B_female_expanded | 23.194 | 23.194 | 0 |
