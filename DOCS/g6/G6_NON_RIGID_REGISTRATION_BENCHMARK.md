# G6 · Non-rigid surface registration

| Method | A held-out retained mm | B held-out proposal mm | B held-out retained mm | B paired gain mm | B backtracked |
| --- | --- | --- | --- | --- | --- |
| R5_nearest | 7.36 | 17.26 | 21.49 | 0.23 | 3/3 |
| R5_regions | — | 17.20 | 21.50 | 0.23 | 3/3 |
| R5_normals | — | 19.36 | 19.80 | 1.93 | 2/3 |
| R5_symmetric | 7.36 | 17.37 | 21.44 | 0.28 | 3/3 |
| R5_symmetric_long | 7.36 | 17.36 | 21.45 | 0.28 | 3/3 |

The canonical mesh fits regularized displacement under nearest-sample ICP with a sparse Laplacian. The arms compare nearest, hard regional labels, region plus normal weighting and symmetric nearest-sample coverage. There is no separate point-to-plane solve or triangle-aware fitting correspondence in this matrix.
