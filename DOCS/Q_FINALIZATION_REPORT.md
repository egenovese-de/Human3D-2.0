# Human3D 2.0 — Q finalization report

**Release v0.2.0 · `480195f05fb2d1ed6c71dceabf4ba54b8bed69db`**
**Lab parent · `9cc1552b201d55e97eacbb1959b009e139ae85d8`**
**Q closure · 39 DONE, 9 BLOCKED · CONDITIONALLY_READY_FOR_M6_PLANNING**

The additional evidence supports planning for triangle-level garment collision validation and lateral-view triage. The largest measured shape/pose sensitivities remain registration (6.36 mm lower surface error) and direction substitution (+7.0 percentage points held-out IoU). The registered bootstrap residual was 23.40 mm. Symmetric optimization reduced it by 0.58 mm in the earlier direct-fit tests. The experiments leave full pose retargeting, independent anatomy representation and beneficial-fit generalization unresolved.

## Final experimental scope

- **Landmarks and rig.** Twelve joint centers were projected independently on 48 views from two identities, yielding 576 anchor records. Matched native and observed XY proxy alignment averaged 55.20% and 58.84% same-image silhouette IoU. Native world landmarks and native presence/visibility were retained. The largest camera projection round-trip residual was about 1.8e−15 m. The largest source parent-chain matrix-element residual was 1.19e−7. These controls establish arithmetic consistency and detector sensitivity to selected anchors. They do not certify cross-rig twist or the detector's semantic convention.
- **Face.** All 26 manual frontal/profile rays intersected independent geometry. The 14 comparable observations span 0.27–6.80 px detector-to-pick distance. Surface response to a one-pixel perturbation reached 20.18 mm near transitions. The picks use one reviewer and resolution-limited feature locations. They form exploratory feature evidence, while the prior head/jaw width oracle remains the regional geometry control.
- **Camera, pose and masks.** The 32-cell camera × limb-direction × shape factorial and 16 calibrated-camera/raster-mask cells were replayed on four articulated identities. For fitted shape, replacing limb directions changed held-out IoU by +8.21 pp with the native fitting camera and +6.20 pp with the calibrated fitting camera, a −2.01 pp camera × direction difference-of-differences. The calibrated raster-mask comparison gave 60.24% → 66.16% and 34.24 → 26.11 mm posed surface error. The upstream joint condition includes raster segmentation, calibrated camera and independent segment directions. Joint centers, v1 evidence, and their downstream effects were measured in separate controls. Full rotation and quantitative anatomy remain outside this combined condition.
- **Geometry transfer.** Nominal 12 and 24 mm transfers failed native face-area validation on all four identities. Damped 3 and 0.6 mm controls and native reconstructed comparators retained canonical structure and passed native pose and bake probes. The exact canonical control tests reproducible release compatibility. Independently transferred skin, material, fingers and face remain unqualified.
- **Garments.** Eighteen neutral shell comparisons were replayed. Twelve new native pose treatments on two identities included eight false-clear cases with 34 intersecting body/garment triangle pairs each. Both virtual cap methods failed across all 24 posed-shell screens. Enclosed envelope and material volume remain unavailable for these native shells.
- **Acceptance and references.** The original frozen acceptance rule was replayed and applied to the complete articulated screening population. All eight articulated fits were rejected. By held-out IoU, this captured two harmful updates, rejected two beneficial updates and left four negligible updates at bootstrap. Both beneficial-IoU updates increased neutral surface error. Reference checks kept every screened treatment, and four native refits isolated the geometry effect of omitting the same profile. Across 16 crossed bakes, omitting the profile reduced mean observed UV from 83.27% to 78.17%. Omitting it from the geometry fit changed held-out IoU by 0.00 to +0.46 pp, while neutral surface error changed by 0.00 to +0.73 mm. RGB error remains unavailable on this independent texture fixture. See [the numerical summary](q/finalization/summary.json).
- **Release verification.** Executed the 69 local regression tests against the archive of the peeled release tag. The finalization diff contains only Lab scripts, documents and evidence. Three repeated controls reproduced identical JSON bytes. The historical Blender editable round-trip remains 7/7.

[Annotation render plate](q/finalization/annotation-plate.png) · [Articulation render atlas](q/followup/articulation-atlas.png) · [Layered Blender render atlas](q/followup/layered-atlas.png) · [Original failure atlas](Q_FAILURE_ATLAS.md)

## EvidenceAdapter v1 field and consumer mapping

| Evidence | Existing provider field | Consumer | Measured effect | Missing capability |
|---|---|---|---|---|
| Photo/candidate association | Photo digest and candidate index | EvidenceAdapter, observation persistence | One of nine synthetic binding cases attached. Only the matching single candidate passed. | No field-level association or cross-photo identity binding. |
| Orientation | Yaw and yaw confidence | Alignment | ≥0.8 confidence required. Detector disagreement above 45° triggered a circular yaw veto. Prior 16-case probe measured +0.51 pp mean posed overlap for yaw. | Full camera, metric scale and rotation uncertainty. |
| Regional visibility | Region, Boolean visibility and confidence | Vision, alignment/fitting observations, appearance and texture gating | Hidden arm suppressed five indices at ≥0.8 and reduced UV coverage by about 2.20 pp in fixed-input bakes. Visible flags leave native observations intact. | Continuous fraction/occlusion, per-pixel visibility and replacement coordinates. |
| Circumferences | None | None for independent values | Unavailable through the provider. | Metric circumference and section definitions. |
| Body proportions | None | Native fitting uses detector-derived relative shape evidence. | Unavailable through the provider. | Independent ratios with landmarks, normalizers and error bounds. |
| Regional volume | None | None | Unavailable through the provider. | Region, physical volume and units. |
| Morphological characteristics | None | None for independent shape | Unavailable through the provider. | Typed morphological measurements and semantic mapping. |
| Anatomical asymmetry | None | None for independent asymmetry | Unavailable through the provider. | Signed side-specific measurements in a common frame. |
| Continuous visibility | None | Consumers use thresholded regional states. | Partial ray-truth fractions were reduced to Boolean values before injection. | Continuous visibility and viewpoint-dependent uncertainty. |
| Measurement uncertainty | Confidence for yaw and Boolean region only | Alignment and visibility threshold gates | Boundary behavior observed at .799 and .8. | Metric uncertainty, calibration and covariance. |

## Closure decision

Q closes as a research phase with the nine dispositions recorded. No residual task met all of its original requirements. The controls are sufficient to prioritize collision validation and calibrate the next phase's benchmark decisions. M6 implementation awaits Project Lead approval, including choices about rig registration, quantitative evidence and base-representation scope.

[Final dispositions](Q_FINAL_BLOCKER_DISPOSITION.md) · [M6 readiness and verification matrix](Q_M6_READINESS.md) · [Reproduction manifest](Q_REPRODUCIBILITY_MANIFEST.md)
