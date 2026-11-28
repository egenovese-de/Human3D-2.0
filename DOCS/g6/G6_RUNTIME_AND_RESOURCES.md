# G6 · Runtime and memory

| Arm | N | Median optimizer phase s | Worst phase s | Median structural and score phase s |
| --- | --- | --- | --- | --- |
| R0_D9 | 10 | 2.05 | 7.23 | 0.25 |
| R0_long | 10 | 3.83 | 8.20 | 0.24 |
| R0_restart | 10 | 4.56 | 7.85 | 0.23 |
| R1_extended | 10 | 6.87 | 12.41 | 0.24 |
| R2_coarse | 10 | 0.54 | 1.90 | 0.26 |
| R2_fine | 10 | 1.07 | 3.66 | 0.23 |
| R2_fine_long | 10 | 0.98 | 7.71 | 0.32 |
| R3_cage | 10 | 0.39 | 1.29 | 0.26 |
| R4_graph48 | 10 | 0.43 | 1.01 | 0.62 |
| R4_graph120 | 10 | 0.47 | 1.18 | 0.58 |
| R5_symmetric | 10 | 3.24 | 4.07 | 0.62 |
| R6_lattice | 10 | 1.60 | 2.72 | 0.59 |
| R6_graph | 10 | 1.42 | 2.95 | 0.61 |

Linux CPU execution used the pinned G5 environment. Maximum per-subject process RSS across the full geometry harness was 931.5 MiB and includes native asset and operator setup. The raw records separate fit and Blender readout, and export metrics record rebind and writing. Operator preparation and concurrent workload timing are not independently isolated for every method. The Windows Server CI describes the small analytic operator suite. i7-1355U/24 GB target performance is unverified.
