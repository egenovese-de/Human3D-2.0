# Regions, landmarks and regional resolution

The tested landmark mapping assigns indices 11/12 to upper arm bone heads, 13/14 to lower arm heads, 15/16 to wrist heads, 23/24 to upper leg heads, 25/26 to lower leg heads and 27/28 to foot heads. MediaPipe observes approximate anatomical cues. The Blender projections are model-rig anchors rather than manual skin markers. The clean A set contains 288 joint comparisons. Median projected error is **5.63 px** across all returned anchors and **5.38 px** above M6's gates. Raw errors, confidences, unsupported regions and individual viewpoints are retained.

| Subject | Mask only | Predicted 2D anchors | Oracle projected joints |
| --- | --- | --- | --- |
| A_adult_asymmetric | 6.70 | 4.41 | 6.79 |
| A_heldout_1 | 5.28 | 5.04 | 5.24 |
| A_high_mass | 2.29 | 2.23 | 2.11 |

Nearest landmark segments were compared with G1 rig-weight triangle labels. Their median region IoUs are head 0.59, left foot 0.77, left forearm 0.68, left hand 0.45, left lower leg 0.82, left thigh 0.57, left upper arm 0.54, neck 0.30, pelvis 0.00, right foot 0.72, right forearm 0.83, right hand 0.64, right lower leg 0.81, right thigh 0.66, right upper arm 0.61, torso 0.61. Labels approximate rig assignment, especially at neck, shoulder and hip transitions. Oracle rig-derived region fitting is listed in the photographic scores. Specialized human parsing with licensed weights, accessories and garment semantics has no downstream qualification. The tested regions and landmark scores demonstrate enough utility to retain landmarks for registration and to treat fitting anchors as optional, feature-specific observations. Calibration requires labelled visible anchors with corresponding rig definitions.

Face, hands and feet occupy small, view-dependent image boxes recorded in `landmark-regions.json`. The body images support gross head/foot outline and the location of visible extremities. Dedicated sharp close-ups and multiple views are required for jaw, fingertips, foot details or identity. Individual face, hand and foot parameter recovery is unqualified.
