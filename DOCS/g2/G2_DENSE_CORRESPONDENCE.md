# Dense correspondence

| Subject | Same-mask geometry error mm | With exact visible barycentric matches mm |
| --- | --- | --- |
| A_heldout_1 | 4.91 | 5.12 |
| A_high_mass | 2.12 | 1.47 |

The exact control reconstructs points using visible triangle IDs and pixel-center barycentric weights in the native topology. Identity reprojection error is recorded, as are sample counts. Different topology samples are deliberately absent. The stereo probe estimates dense epipolar correspondence from two RGB-like grayscale views and measures error against known projected depth. This gives a separate approximate cross-view correspondence benchmark. It does not assign UV identity, regions or chirality on ordinary photographs. A DensePose or other learned body-surface pipeline was not admitted or run. Its chart-to-MakeHuman topology mapping must be established and tested before adoption.
