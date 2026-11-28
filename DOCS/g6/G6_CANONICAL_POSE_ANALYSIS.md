# G6 · Canonical pose and posture

| Subject | Native mm | Arm-direction mm | All limb-directions mm |
| --- | --- | --- | --- |
| B_female | 22.59 | 16.65 | 37.16 |
| B_female_expanded | 21.09 | 16.39 | 37.68 |
| B_male | 18.56 | 9.50 | 40.34 |
| B_male_expanded | 18.58 | 10.50 | 39.85 |

For the independent matched-geometry control the baseline row in this table is the native R0_D9 shape. Orientation transfer uses frozen authored MB-Lab directions and the product skin weights. Landmark anchors are normalized with the original G5 scale and floor. It is an explicit pose intervention, and scores against the same unmoved reference. The all-limb control introduces a failure rather than a valid normalization. The A, T and X configurations are fixed direction probes of one MakeHuman holdout. Raw collision counts are in structure.json. Use this evidence to preserve the native canonical contract pending wider pose conditioning and landmark correspondence tests.
## Four-pose crossing control

| Pose | Disjoint-index crossing pairs | New relative to native |
| --- | --- | --- |
| native | 42 | 0 |
| A | 42 | 0 |
| T | 42 | 0 |
| X | 42 | 0 |

The single control shares the same native pair set in all four poses. This does not establish a canonical advantage for A, T or X. There is no controlled multi-family result for axilla, groin separation, or conditioning.
