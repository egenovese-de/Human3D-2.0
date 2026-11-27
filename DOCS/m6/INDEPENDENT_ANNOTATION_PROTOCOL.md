# Independent anatomical annotation protocol

Use source anatomical LEFT and RIGHT. The indices follow the [official MediaPipe Pose Landmarker ordering](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker#pose_landmarker_model). The anatomical targets below are operational evaluation definitions. Verify their equivalence to detector semantics separately.

| Index | Definition | Reference type |
|---|---|---|
| 0 | Nose tip at the most anterior central skin point | Surface |
| 1, 4 | Medial canthus, left then right | Surface |
| 2, 5 | Center of the visible iris or marked eye aperture center for neutral gaze, left then right. Record which convention applies. | Surface |
| 3, 6 | Lateral canthus, left then right | Surface |
| 7, 8 | Tragus midpoint, left then right | Surface |
| 9, 10 | Oral commissure, left then right | Surface |
| 11, 12 | Glenohumeral center, left then right | Joint |
| 13, 14 | Midpoint between humeral epicondyles, left then right | Joint |
| 15, 16 | Radiocarpal center, left then right | Joint |
| 17, 18 | Fingertip of the fifth digit, left then right | Distal surface |
| 19, 20 | Index fingertip, left then right | Distal surface |
| 21, 22 | Thumb tip, left then right | Distal surface |
| 23, 24 | Femoral head center, left then right | Joint |
| 25, 26 | Center of the femoral condylar axis, left then right | Joint |
| 27, 28 | Midpoint of the malleolar axis, left then right | Joint |
| 29, 30 | Posterior calcaneal surface point, left then right | Distal surface |
| 31, 32 | Second-toe distal surface point, left then right. Verify toe equivalence with separate first-toe and second-toe controls. | Distal surface |

## Records and blind procedure

Record fixture and source-family IDs, approved asset license and revision, mesh hash, pose hash, calibrated camera intrinsics/extrinsics, image size and hash, annotator pseudonym, timestamp and protocol version. For each indexed landmark record source mesh position in metres, surface triangle and barycentric coordinates when available, and a covariance or uncertainty bound in millimetres. A subsurface center requires authored rig or skeletal geometry references rather than a nearest-skin point. Source artwork that lacks sufficient skeletal structure receives an unavailable center. Retain all excluded cases and their reason.

Independent annotators work from the calibrated asset and source rig without detector outputs, candidate fits, or each other's coordinates. Resolve conflicts by recording the original picks, inter-rater distances and uncertain conclusions. Repeated picks from one process measure repeatability. They provide no independent review. Keep detector outputs sealed until references and split hashes are frozen.

Report surface visibility by first-hit ray from the camera to the reference point with a ray-depth tolerance derived from mesh precision. Distinguish outside-frustum, self-occluded, garment-occluded, ambiguous and visible. A joint center is subsurface by construction. Record its projection and uncertainty separately from visibility of the region bracketing the joint. Detector confidence can be evaluated against these labels and is distinct from an independent visibility label.

Blender source axes convert to canonical axes with `(X,Y,Z) → (X,Z,-Y)`. Convert metres to decimetres only at the native application boundary. Preserve camera intrinsics and image crop/resize history. Compare normalized detector image coordinates in image space after applying the source size and pixel convention. Compare detector world coordinates only after declaring the origin, scale, orientation and uncertainty. Do not compare camera-relative detector depth to absolute metric depth.

## Joint-frame evidence

Record longitudinal direction from independently labeled centers and a transverse reference from paired landmarks or known anatomy. Provide reference axes for shoulders/hips, epicondylar elbow and knee hinges, wrist/hand, ankle/foot, pelvis, spine, neck and head. Use orthogonalized longitudinal and transverse vectors and record a right-handed basis, rest-pose parent frame and source-to-target sign convention. Reject near-collinear evidence for axial twist. Run signed positive and negative rotations in all three local axes, then compare local and global rotations, joint center and segment length, weighted skin points and foot contact. Numerical frame closure is a separate result from anatomical frame equivalence.
