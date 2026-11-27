# Contour objectives

| Family | RGB IoU | RGB signed occupancy | RGB Chamfer | RGB SDF | RGB contour + gaps |
| --- | --- | --- | --- | --- | --- |
| A original | 5.65 | 8.75 | 5.22 | 5.21 | 4.52 |
| A held-out | 7.77 | 9.51 | 7.57 | 7.17 | 7.30 |
| B independent | 20.59 | 23.22 | 19.87 | 20.02 | 20.80 |

Values are mean symmetric 3D error in mm, with the RGB mask family and the same fit schedule. The binary raster induces plateaus for subpixel perturbations, including in contour scores. Truncated symmetric Chamfer mitigates the effect of distant outliers and supplies direction over larger offsets. The narrow-band SDF used here evaluates in about twice the fitting time of Chamfer and offers no reliable 3D advantage. Keep IoU and signed occupancy as diagnostics. Keep a conservative gap penalty conditional on visibility and registration.

The loss landscapes vary one camera parameter at a time, or vary native torso width around neutral without solving the other parameters. These one-dimensional profiles establish sensitivity and plateaus, not global convexity. See the measured curves in `controls/*/controls.json` and `G2_Contour_Landscapes.png`.
