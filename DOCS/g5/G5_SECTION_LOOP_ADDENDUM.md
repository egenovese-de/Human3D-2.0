# G5 addendum — torso cross-sections

Re-measurement of three archived MakeHuman geometries. High mass is a development subject. Held-out 1 and slim are evaluation subjects. Four fixed metric planes per subject reproduce the primary chest, abdomen, waist and pelvis definitions.

The method intersects the mesh triangles with each plane, then follows closed edge-connected contours. The largest closed contour crossing the body midline defines the torso section. Circumference is the length of the actual loop. Shape error is the mean of two directed distances from arc-length samples to the other loop’s segments. Measurements retain the original world alignment and the validated local fallback.

| Arm | Shape error mean, mm | Absolute circumference error mean, mm | Sections |
| --- | ---: | ---: | ---: |
| D0 | 10.55 | 58.19 | 6 |
| D1 | 6.10 | 22.50 | 6 |
| D2 | 7.97 | 25.74 | 6 |
| D3 | 6.20 | 17.00 | 6 |
| D4 | 8.11 | 21.56 | 6 |
| D5 | 6.61 | 23.35 | 6 |
| D6 | 8.92 | 26.86 | 6 |
| D7 | 6.20 | 17.00 | 6 |
| D8 | 8.92 | 26.86 | 6 |
| D9 | 6.98 | 37.08 | 6 |
| L0 | 10.36 | 57.54 | 6 |

The table averages the abdomen, waist and pelvis on each of two held-out bodies. These six sections represent two independent subjects. The chest plane lies near the arm attachments. A small change in geometry can join or separate arm and torso contours there. For example the slim reference midline-crossing chest loop is 127.7 cm. Its D0 counterpart is 83.7 cm. All chest rows are retained as diagnostics and excluded from the pooled torso comparison. Circumference therefore describes the admitted measurement loops and should not be read as a precise anthropometric chest measure.

Signed circumference and area errors, shape P95, and local fallback identities are available in G5_SECTION_LOOP_MEASUREMENTS.json. The original evidence archive includes publishable geometry for three MakeHuman subjects. Independent MB-Lab circumference and cross-section effects remain open. G5-023 remains partial.

The square-prism control recovered an analytical 8 cm perimeter, 4 cm² area, and zero self-distance.
