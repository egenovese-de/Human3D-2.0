# Source and release rig correspondence

Source anchors and all stored matrices are in Blender XYZ metres. The release model mapping is (X, Z, −Y), followed by the documented scale and floor alignment. Use the rotation part of that axis map to transform rotation matrices by conjugation. Matrix records use column vectors, with homogeneous matrices serialized as rows.

| Source MB-Lab | Release homologous chain | Status |
|---|---|---|
| upperarm_L/R | upperarm01.L/R | Direction and joint-center proxy |
| lowerarm_L/R | lowerarm01.L/R | Direction and joint-center proxy, twist frame unresolved |
| hand_L/R | wrist.L/R | Direction and joint-center proxy, axial convention unresolved |
| thigh_L/R | upperleg01.L/R | Direction and joint-center proxy |
| calf_L/R | lowerleg01.L/R | Direction and joint-center proxy |
| foot_L/R | foot.L/R | Direction and joint-center proxy, sole and toe-frame registration unresolved |
| pelvis, spine01/02/03, neck, head | Native axial chain | Source motion recorded, independent cross-rig segment and rest-frame correspondence unresolved |
| Auxiliary twists and digit chains | Release auxiliary and digit topology | Correspondence unvalidated |

For each source bone, rest local is inverse(parent rest global) times child rest global. Posed local is inverse(parent posed global) times child posed global. The tested source relation is posed local ≈ rest local times Blender pose basis. The global rest-to-pose change is posed global times inverse(rest global). Retargeting requires each rig's verified bind-frame and twist convention. Source matrix closure provides a source invariant. Native pose consumes silhouette/landmark-derived directions, depth ratios and wrist cross axes, so the evaluated release input is a subset of the full source motion.

A full comparison should recover positive and negative prescribed rotations around three local axes independently and in composition, including pelvis/spine and wrist/foot axes, before scoring downstream camera/pose/shape interactions. Compare both global and parent-relative geodesic errors. Score joints in millimetres and evaluate posed meshes with fixed cameras, scale and stance. A segment axis alone leaves one rotation degree of freedom unobserved.
