# G6 · Structural validation

| Method | A held-out retained mm | B held-out proposal mm | B held-out retained mm | B paired gain mm | B backtracked |
| --- | --- | --- | --- | --- | --- |
| R1_extended | 7.35 | 19.03 | 19.03 | 2.69 | 0/3 |
| R2_fine | 6.61 | 13.42 | 13.42 | 8.30 | 0/3 |
| R3_cage | 6.70 | 19.38 | 19.38 | 2.35 | 0/3 |
| R4_graph120 | 7.28 | 19.16 | 20.37 | 1.35 | 3/3 |
| R5_symmetric | 7.36 | 17.37 | 21.44 | 0.28 | 3/3 |
| R6_lattice | 6.61 | 10.95 | 17.07 | 4.65 | 3/3 |

All fit arms use the existing M7 rebind check and relative face-normal screen before Blender. Blender BVH overlaps record disjoint-index triangle pairs. For advanced proposals, new pairs or relative face flips cause bounded backtracking against the applicable M7 parent. Pre-existing pairs, reference pairs and proposal pairs are separate. The final metric retains fallback results, including zero deformation where necessary. A retained fit can inherit existing crossings. The archive records topology, numeric hashes, and pre/post structural reductions. A topological proof, analytic collision certification and anatomical semantic validation remain open.
## Sampled volumetric constraint

The new R2 volume-checked results evaluate the same global coefficient scale through the sampled determinant and surface screens. See G6_FFD_BENCHMARK.md. The refitted fine-FFD diagnostic and the single-field candidate are separate outputs. Regional and posed intersections are not inferred from determinant samples.
