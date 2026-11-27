# M6 blocker resolution

| Task | Technical outcome and release impact |
|---|---|
| M6.2-005 | All 33 image indexing and coordinate probes passed. Independent detector-equivalent landmark semantics, including separate surface/subsurface labels and visibility agreement, still need actual independent annotations on calibrated realistic assets. |
| M6.2-007 | 66 signed analytic rotations checked source and target frame construction. This validates conversion with authored axes. Anatomical transverse correspondence, weighted deformation and contact under independently confirmed axes remain unqualified. |
| M6.3-002 | New calibrated coordinate controls cannot validate a direction estimator on their own. The existing attenuation candidate missed the direction/no-IoU-loss gate. A realistic independently annotated direction cohort is outstanding. |
| M6.3-003 | Camera-relative landmark depth and axial rotation cannot be promoted without the independently calibrated joint map and depth reference. |
| M6.3-004 | An observable transverse axis is required for twist, wrist and foot orientation. Absolute contact references and independent spine/pelvis orientation remain outstanding. |
| M6.3-007 | The candidate still lacks a pose/camera improvement passing the independent direction and geometry gates. |
| M6.4-007 | The frozen rule failed to accept beneficial Q cases. An independent realistic cohort with prespecified beneficial, harmful and negligible labels for the three quality axes remains unavailable. |
| M6.4-008 | The opt-in torso evidence consumer is supported on a known-effect control. Independent fit acceptance and held-out regional gains are still needed for automatic geometry or acceptance promotion. |
| M6.5-001 | Facial feature definitions are specified. Independent repeated human annotations, disagreement bounds and profile correspondence remain outstanding. |
| M6.5-002 | Bounded facial changes require the independent facial measurements above. Texture and silhouette are insufficient for qualification. |
| M6.5-006 | Existing utility rules accept incompatible photographs. Separate identity, geometry and appearance policies await an independently qualified, local identity consistency mechanism. User-controlled inclusion remains the safe path. |
| M6.6-002 | The separately sourced clothed Cesium Man adversarial control was added. It is stylized and contains one identity. The two poses cannot qualify realistic anatomy, face or independent holdout improvement. |
| M6.6-004 | Four native layered round-trips passed. Workshop and Woodland still fail body contact screening. Woodland's preliminary clearance introduced two posed shell self-intersections and was rejected. The historical independent ring pair still has neutral/posed layer crossings. |
| M6.6-008 | Release remains blocked by the USDZ, anatomical, pose, facial and independent quality gates. |

## Local garment repair alternatives

Indexed repair separates exact obstacles in neutral and posed geometry while working in the garment's bind space. Workshop has 9 neutral and 115 posed intersections at ease 6 mm, spanning one and three connected shell regions respectively. Woodland at the same ease has 16 posed intersections in one region. Its garment fit's minimum-contact fallback still has 14 posed intersections. The historical ring configuration with the old 1.25 radial multiplier and projection treatment retained 186 neutral and 190 posed layer crossings. The multiplier is historical fixture reproduction. It is outside the new correction.

The following alternatives failed qualification on the affected history: localized plane projection alone on folded areas, projected Laplacian spreading, stronger adjacent displacement extension, correspondence-based posed normal offset, smaller motion safety gap and eliminating emerging self intersections pair by pair. The local planar solver remains useful for controlled shallow crossings. The accepted candidate keeps strict neutral/posed validation and rejects new self crossings, including ones extending beyond a shared vertex. No rejected alternative was enabled by default.

The [completion evidence](https://github.com/egenovese-de/Human3D-2.0/tree/3bb6aefdefc72a71f4f416e58e4a0e6514c412f1/DOCS/m6/completion) gives source and target triangle indices, connected shell regions, dominant skin bones, timing and per-control visibility outcomes. The Workshop Blender localization PNG is reproducible from the Lab pack/render commands and has SHA-256 `b71041c0389142efb5ab20b466a19c9e4804a9a0fca60853ecea40bfac2636dd`.
