# Viewpoint and reference-count information gain

| Case | Front | Side | Oblique | Front + side | Front + side + rear | Four |
| --- | --- | --- | --- | --- | --- | --- |
| A_high_mass | 4.47 | 2.89 | 3.91 | 3.21 | 3.34 | 2.93 |
| A_heldout_1 | 8.18 | 5.84 | 7.87 | 6.01 | 6.22 | 6.59 |
| B_female | 27.63 | 24.00 | 20.57 | 20.67 | 20.79 | 20.61 |

These rows use RGB border-key profiles with calibrated projections and report mm. The two A large-view controls instead use raster oracle masks and fixed orthographic observation pose.

| Case | 2 views | 4 | 8 | 16 | 30 |
| --- | --- | --- | --- | --- | --- |
| A_heldout_1 | 5.47 | 5.00 | 4.96 | 4.85 | 5.02 |
| A_high_mass | 2.17 | 2.29 | 1.67 | 1.83 | 1.70 |

Frontal plus side views supply complementary width and depth. A rear view can add region visibility, although its orthographic outline is largely the horizontal reflection of the front outline. Obliques change separation and support additional shapes. Diminishing gains in these controls are visible around 4–8 independent viewpoints. The small sample, calibrated cameras and fixed pose prevent a general recommendation for 30 photographs. The large view-count sets at regular azimuth spacings are not strictly nested.
