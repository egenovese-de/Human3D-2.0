# Human3D 2.0 Q follow-up

Release `480195f05fb2d1ed6c71dceabf4ba54b8bed69db`. Follow-up Lab parent `c664fabe716ced28bc43d5e23f974b307234f19f`.

39/48 tasks are DONE and 9 remain BLOCKED. The [backlog](BACKLOG_Q.md) is authoritative for closure. The [reconciliation](Q_BLOCKER_RECONCILIATION.md) covers every original blocker and all five additions. Historical pilot and holdout measurements remain available in their original files.

- The largest controlled geometry change was stance registration at 6.36 mm across four prior identities. A bounded symmetric direct surface objective improved the registered bootstrap by an additional 0.58 mm.
- In 32 factorial cells, reference segment directions improved mean fixed-camera held-out IoU at bootstrap from 61.8% to 68.8% with the native fitting camera. Native fitting could then improve or reduce geometry accuracy, depending on the camera treatment.
- Paired clothing fixtures showed accurate clothed masks with larger discrepancies against the underlying body. A fixed-camera neutral fit reported a different surface error even when the clothing occupied the same physical subject.
- The calibrated appearance control distinguished color accuracy, observed coverage, chart seam discontinuity and hidden leakage. The three-pixel displacement stress case increased visible RGB mean absolute error from 1.80 to 32.66 levels per channel.
- Four production garment conditions with zero sampled violations still had 34 intersecting triangle pairs each under Blender BVH. Open shells were excluded from volume estimates.
- A USD-capable Blender 4.5.17 LTS distribution successfully imported seven release-format USDZ files, including four articulated canonical layered controls and one independent registered layered control. Body and garment editing and save/reopen were verified directly.

| Evidence | Scope |
|---|---|
| Dataset | 17 preset source geometries, including 13 human-style and 4 exploratory stylized geometries, plus 2 historical base geometries and correlated deformations. The prespecified articulated extension contains 29 fixtures and 86 renders. |
| Pose | 14 independent-rig cases from two identities, plus matched frontal and profile contact diagnostics. Each valid alignment has 16 named mapping entries. |
| Geometry | Four prior holdout identities in the direct and photographic protocols, including 32 pose-camera-shape cells and three bounded direct-fit schedules per identity. |
| Fit acceptance | 12 development and 8 identity-evaluation input configurations. |
| Vision | 132 degradation/orientation evaluations, 56 regional visibility ray checks and 16 evidence substitution cases with four conditions each. |
| Face | 13 identity scans and 14 controlled expression/profile cases, each with 25 release-control evaluations. |
| Appearance | Seven controlled UV conditions with 8,899 sampled triangle-interior entries per condition. |
| Clothing | 12 paired conditions across two identities, 24 detector images, 18 native shell collision comparisons and seven editable USDZ imports. |
| Tests | 69/69 local tests on the release checkout. |

The [M6 decision matrix](Q_M6_RECOMMENDATIONS.md) distinguishes measured interventions, unresolved evaluation dependencies and priority for subsequent validation.
