# Camera and scale sensitivity

| Perturbation | A high mass width MAE px | A heldout 1 width MAE px | A high mass normalized MAE |
| --- | --- | --- | --- |
| weak_perspective | 3.33 | 3.61 | 0.016 |
| focal_+8pct | 7.24 | 7.14 | 0.002 |
| roll_5deg | 1.80 | 1.95 | 0.006 |
| elevation_zero | 4.06 | 4.57 | 0.013 |
| distance_450_same_angular_scale | 1.69 | 1.98 | 0.007 |
| yaw_+10deg | 2.93 | 2.83 | 0.010 |
| crop_translation | 23.89 | 21.68 | 0.014 |

The reference is a known full-perspective camera at 260 cm, with 12° elevation and 35° yaw. Distance varies at fixed angular scale in one control. Normalized width divides foreground width by visible image height at homologous image-height fractions. It damps pure scaling error and remains biased by perspective, rotation, occlusion and truncation. Absolute metric dimensions require a scale anchor. EXIF focal length can supply a prior with sensor geometry; EXIF alone supplies no physical stature. M6 camera and torso residuals per view are preserved, with camera-frame yaw conventions differing between M6 and the rendering harness. The 9° yaw, rotation and scale perturbations in the fitting benchmark deliberately combine three registration errors and do not infer the individual shares. Single-axis projection controls above isolate the individual changes.
