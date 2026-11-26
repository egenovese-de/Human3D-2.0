# Q calibrated landmark protocol

The reference is the independent MB-Lab geometry and rig. Author landmark picks with detector overlays disabled. Record subject, mesh hash, render hash, oriented camera matrix, image dimensions, view angle, feature, convention, polygon and barycentric or metric position. Use side labels from the subject's perspective. The table defines the working anatomical convention, pending empirical equivalence to the detector's training labels.

| Indices | Feature | Convention and status |
|---|---|---|
| 0 | Nose | Nasal tip, first skin intersection in the chosen view. Pilot picks recorded. |
| 1, 2, 3 | Left inner, center, outer eye | Medial canthus, eye opening center and lateral canthus. Center pilot only. Mark lash or closed-eye ambiguity. |
| 4, 5, 6 | Right inner, center, outer eye | Same conventions, right side. Center pilot only. |
| 7, 8 | Left and right ear | Tragus region anterior to canal. Left pilot pick only, precise detector semantic correspondence remains open. |
| 9, 10 | Left and right mouth | Oral commissure on skin. Pilot picks recorded. |
| 11, 12 | Left and right shoulder | Humeral center from upper-arm bone head. Separate surface comparison at acromion. |
| 13, 14 | Left and right elbow | Flexion center from lower-arm bone head. Separate surface comparison at lateral epicondyle. |
| 15, 16 | Left and right wrist | Hand bone head for joint center. Separately record midline dorsal wrist surface. |
| 17, 18 | Left and right pinky | Distal pad center on little finger. Unannotated. |
| 19, 20 | Left and right index | Distal pad center on index finger. Unannotated. |
| 21, 22 | Left and right thumb | Distal pad center on thumb. Unannotated. |
| 23, 24 | Left and right hip | Femoral center from thigh bone head. Separately record greater trochanter projection on skin. |
| 25, 26 | Left and right knee | Flexion center from calf bone head. Separately record center of patellar surface. |
| 27, 28 | Left and right ankle | Foot bone head for joint center. Record lateral malleolus separately. |
| 29, 30 | Left and right heel | Posterior calcaneal skin apex in neutral foot coordinates. Unannotated. |
| 31, 32 | Left and right foot index | Distal second toe skin anchor. Unannotated and detector semantics unverified. |

Map Blender XYZ metres into camera coordinates with the inverse camera-to-world matrix. For square orthographic view scale s, normalized x is 0.5 + X/s and y is 0.5 − Y/s. Multiply by oriented width and height for pixel coordinates. Preserve pose-camera depth separately. The canonical release model path uses axes (X, Z, −Y) and decimetres. MediaPipe world-landmark inputs are inferred hip-centered 3D data. No calibrated external world-coordinate substitution is certified by these tests.

For a surface landmark use a first-hit camera ray. To verify a 3D point's visibility, compare its depth with the first-hit depth at the projection and flag missing rays, intervening surfaces and depth ambiguity separately. For a joint center, record a separately annotated observability class for the body region around the joint. Skin preceding a subsurface center is expected. The pilot reports native observability and in-frame status, with synthetic occlusion truth and joint semantic uncertainty left null.

Freeze picks and masks before detector comparison. Obtain two blind independent annotation passes for detector-equivalent claims. Report disagreement in pixels and 3D millimetres per feature and visibility class. Where complementary views clearly identify the same feature, report their 3D disagreement. The pilot uses a single reviewer and a four-neighbor ray sensitivity check. That check measures spatial sampling sensitivity and does not estimate inter-annotator disagreement.
