# Visual hull and static stereo

| Case | 2-view IoU | 4-view IoU | 8-view IoU | 16-view IoU | 30-view IoU | 30-view excess L |
| --- | --- | --- | --- | --- | --- | --- |
| A_heldout_1 | 0.665 | 0.860 | 0.921 | 0.938 | 0.937 | 2.60 |
| A_high_mass | 0.662 | 0.850 | 0.918 | 0.932 | 0.939 | 2.63 |

The 2 and 3 cm voxel grids intersect calibrated silhouettes. Ray parity against reference triangles approximates ground-truth occupancy. Voxel boundary distance, volume over/underestimation, regional bands, allocation and wall time are recorded. Concavities outside the visible silhouette constraints remain unresolved. The four-view fit plus a penalty derived from the same four-view volume compares to the four-mask fit in `controls/surface.json`. Its limited change does not justify enabling voxel carving by default. Silhouettes in different articulated poses cannot be intersected in a common neutral voxel grid.

| Rectified synthetic stereo | Coverage | Median pixel error | Median depth mm | Plane baseline mm |
| --- | --- | --- | --- | --- |
| smooth_facet_shading | 1.000 | 0.147 | 18.82 | 31.30 |
| analytic_texture | 1.000 | 0.125 | 15.89 | 31.30 |

Stereo uses an 8 cm baseline and SGBM, fixed known camera intrinsics, same pose and static scene. The controlled analytic texture is attached to the geometry. Even smooth facet shading gives matching cues, so real smooth skin may perform worse. The left-right occlusion rejection control showed weak rejection. Human motion, specular lighting and arbitrary separate captures were not qualified. No independent stereo M6 integration is recommended.
