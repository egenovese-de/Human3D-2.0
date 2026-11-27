# Dense anatomical profiles

| Family | RGB sparse profile | RGB dense profile | RGB contour alone | RGB contour + gaps |
| --- | --- | --- | --- | --- |
| A original | 4.95 | 5.10 | 5.22 | 4.52 |
| A held-out | 7.56 | 7.61 | 7.57 | 7.30 |
| B independent | 21.48 | 19.82 | 19.87 | 20.80 |

The 384 px extraction records left/right envelope, total occupied width and internal gap for all rows. The fit samples a two-pixel grid at 144 px. Its sparse version uses every tenth. G1 triangle-plane sections provide width, depth, anterior/posterior extent and convex-hull perimeter for 16 fixed model heights. Image rows are compared in registered coordinates. Simultaneous intersections with arms and legs remain confounders. Frontal and rear widths, lateral depth, and oblique transitions are visible; local limb and torso profiles require a trusted anatomical partition, with no physical length inferred from raw pixels. An extracted hull perimeter is a geometric proxy.

Dense profiles do not have a robust downstream advantage over the simpler contour+gap probe. Use for diagnostic attribution and optional anatomy-normalized residuals after G3. Local limb axes, continuous region labels and reliable clothing boundaries remain open.
