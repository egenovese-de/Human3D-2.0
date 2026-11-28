# G6 · Optimizer capacity

| Method | A held-out retained mm | B held-out proposal mm | B held-out retained mm | B paired gain mm | B backtracked |
| --- | --- | --- | --- | --- | --- |
| R0_D9 | 2.97 | 19.41 | 19.41 | 2.32 | 0/3 |
| R0_long | 2.88 | 20.16 | 20.16 | 1.56 | 0/3 |
| R0_restart | 2.60 | 18.64 | 18.64 | 3.08 | 0/3 |
| R2_fine_budget6 | 6.61 | 13.84 | 13.84 | 7.89 | 0/3 |
| R2_fine | 6.61 | 13.42 | 13.42 | 8.30 | 0/3 |
| R2_fine_long | 6.61 | 13.34 | 13.34 | 8.38 | 0/3 |
| R5_symmetric_budget6 | 7.36 | 16.80 | 21.47 | 0.26 | 3/3 |
| R5_symmetric | 7.36 | 17.37 | 21.44 | 0.28 | 3/3 |
| R5_symmetric_long | 7.36 | 17.36 | 21.45 | 0.28 | 3/3 |

The two native long-budget runs share residual definition and bounds while changing only start values. G5 D9 also differs in sample construction and objective schedule. The evaluated 6, 14 and 28 outer-iteration brackets compare optimization progress within a family. Equal iteration limits between method families are measured separately from elapsed compute. Solver and correspondence curves, wall time and termination codes are archived. These finite budgets establish observed ceilings under their own schedules.
