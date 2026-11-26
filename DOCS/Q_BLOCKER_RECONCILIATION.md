# Q follow-up blocker reconciliation

The original 29 DONE entries retain their historical designations. A full historical replay was outside these case-level interventions. In the table, BLOCKED means that the requested evidence is still incomplete. Each row names the remaining dependency and the work executed toward it.

| Task | Status | Executed evidence and remaining dependency |
|---|---|---|
| Q1-006 | DONE | Two independent MB-Lab rigs, prescribed pelvis tilt/rotation, sustained spine flexion/extension and lateral curvature, asymmetric clavicle and limb poses, and separate unilateral torso, shoulder and calf shape changes. Compared 14 cases at fixed camera and alignment with regional error and recorded source rest/pose transforms. |
| Q2-004 | BLOCKED | Audited 33-landmark release semantics and earlier selected anchor proxies. The MB-Lab armature supplies joint locators. Calibrated detector-equivalent surface landmarks for ears, eyelids, lips and distal digits still require semantic annotation and independent validation before injection. |
| Q2-005 | BLOCKED | Validated region visibility against sampled Blender masks and ran yaw, visibility and combined substitutions. Schema v1 exposes yaw and coarse region flags. Independent ground-truth shape, circumferences and continuous regional measurements have no field or consumer. |
| Q2-007 | BLOCKED | Combined calibrated camera, raster masks and limb-direction proxies. Full joint oracle requires independently validated landmark definitions, occlusion and full rotation mapping. Evidence substitution was measured independently. |
| Q2-008 | BLOCKED | Failed native validation at nominal 12 and 24 mm; damped transfers passed native pose, texture bake and garment probes while preserving canonical topology, UV and skin attachment. Full geometry-oracle treatment still requires anatomically validated mapping of fingers, face and joints, plus independent UV/material correspondences for matched texture and garment comparisons. |
| Q4-005 | DONE | Ran bare, close-fitting top, shorts, trousers, loose and layered silhouette fixtures on two independent bodies. Measured detector mask against both clothed and underlying geometry, landmark observability, yaw and fixed-camera neutral surface error. |
| Q5-001 | BLOCKED | Quantified cranial, midface and jaw-band surface envelopes. Independently identifiable and calibrated anatomical face points and matched native semantics remain necessary for landmark accuracy. |
| Q5-002 | DONE | Measured 25 head/jaw control pairs on 13 human-source presets and on 14 controlled profile/expression meshes from two identities. The tests cover cranial width/depth, jaw opening, smile, unilateral cheeks and nasal projection. Native head/jaw width lacks independent depth, nose, cheek and expression axes. |
| Q5-003 | DONE | Six pose conditions plus independent asymmetric geometry on two rigs. Compared named homologues using independent rest-to-posed changes and parent-relative changes in a common world basis. Position, direction, local/global rotation and length are reported separately. |
| Q5-004 | DONE | Evaluated 28 frontal/profile conditions with controlled wrists, forearm torsion, raised feet, asymmetric bent-knee stance and seated posture. Used reference sole masks from independent skin weights, calibrated floor coordinates and inter-foot clearance. Physical contact forces fall outside the release placement model. |
| Q5-005 | DONE | Independently ray-rendered analytic colors, four-patch chart, documented display-domain exposure and controlled pixel shift on canonical UV correspondence. Measured visible RGB, observed UV, hidden leakage and sensitivity to spatial displacement. |
| Q5-006 | DONE | Measured paired UV seam samples, mask-gated versus unmasked known occluder, hidden texels and padding/default behavior under matched canonical geometry. |
| Q5-007 | BLOCKED | Independent pattern and boundary probes, sampled signed gaps and triangle-level intersection counts were executed. Virtual hem caps were tested. Native cap volumes failed self-intersection validation. Independent top controls yielded envelope proxies; lower controls also failed closure validation. Defensible native volumes remain missing. |
| Q5-008 | DONE | Imported two single-garment controls, four native layered controls and one independent registered layered package directly with Blender 4.5.17 LTS. Confirmed edit/save/reopen, armature binding, pose persistence, vertex motion and safe removal. The independent male transfer failed export; the passed female transfer was heavily repaired and remains an editability control. |
| Q7-001 | DONE | Same-subject bootstrap registration, native and calibrated photographic fit, existing one-sided and symmetric direct fitting, and alternate bounded seeds/schedules. Results quantify the tested stance and optimization effects. Two MakeHuman adult-basis controls passed native rebinding and were scored separately. |
| Q7-002 | BLOCKED | Development-only threshold grid and separate subject evaluation, including single-photo cases. Held-out group provided no beneficial fits, so false rejection of beneficial held-out fits is unidentified. Ran an explicit profile leave-out probe. Per-region plausibility with beneficial held-out fits remains open. |
| Q7-003 | BLOCKED | Completed 32 fixed-evaluation factorial cells. Ran a second camera/shape pass from the native-pose cell. Full validated reference rotation and alternating under all matching conditions remain open. The substitute controls segment orientation. |
| Q7-004 | BLOCKED | Tested seven reference treatments per identity and assessed simple view-selection thresholds. All different identities passed both policies. Matched geometry/appearance refits with calibrated texture truth and a validated identity-consistency score remain open. |
| Q7-005 | DONE | Completed 132 detector cases with confidence, profile orientation, masks, review reasons and release pose/alignment silhouette effects. Documented progressive severity levels and transitions. |

## Detector landmark validation boundary

| Indices | MediaPipe semantics | Required ground-truth annotation |
|---|---|---|
| 0–10 | Nose, left and right inner/center/outer eye, left/right ear and left/right mouth corner | Surface ridge/tip and feature points picked on the calibrated mesh. Use per-feature definitions and repeat annotations. |
| 11–16 | Shoulders, elbows and wrists, left/right | Compare joint-center proxies and surface-defined locations separately. Record the convention used for each value. |
| 17–22 | Pinky, index and thumb, left/right | Distal surface anchors with independent hand annotations and occlusion checks. |
| 23–28 | Hips, knees and ankles, left/right | Compare center-of-rotation proxies and surface anchors separately. |
| 29–32 | Heels and foot indices, left/right | Surface-defined heel and distal forward foot landmarks. Rig foot endpoints do not establish these coordinates. |

The coordinate path is height-aligned Blender XYZ metres, orthographic camera rays, pixels, then normalized EXIF-oriented coordinates. The release world-landmark linear axes and origin require a separate tested conversion. Surface points require first-hit visibility checks. Subsurface centers require an explicit visibility convention independent of the surface ray hit. The reviewed ground-truth protocol must record out-of-frame, occluded and uncertain labels, using independent repeated annotation and pixel/mm disagreement bands. These checks have been implemented for region visibility only.

## Anatomy evidence consumer audit

- The adapter binds to one candidate by photo digest and candidate index, records provider/model/schema provenance and falls back to native detections for an unavailable provider.
- Alignment uses yaw confidence ≥0.8 and vetoes provider yaw over 45° away from the detector's circular yaw. The final alignment searches a neighborhood around the selected yaw. External yaw therefore controls a prior rather than a calibrated camera transform.
- Vision and appearance use the same confidence gate for hidden region flags. Vision suppresses observations, and appearance marks strongly region-bound vertices as unavailable. True visibility cannot synthesize missing x/y/world landmarks. The adapter does not override native full-body review.
- The supported regional oracle used ray-derived projected surface visibility and a prespecified 5% cutoff. The resulting Boolean is a property of the sampled fixture and cutoff. The deterministic confidence is not a probability of API correctness. Area, morphology, body-size and circumference annotations remain outside the v1 fields.
