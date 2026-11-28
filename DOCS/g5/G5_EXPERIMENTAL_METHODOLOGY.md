# G5 experimental methodology

The study reuses the pinned G4 cohort and uses the qualified M7 project service as D0. It retains the original M7 mask detector, contour fit, native 582-target dependency evaluator, 17 fitted global and regional controls, admission logic, and rebind gate. G4 historical distances refer to a different optimizer, camera set and evidence extraction path. G5 uses actual M7 service invocations on the same RGB fixture set supplied to the G5 interventions.

| Difference from the G2 depth probe | G5 treatment |
| --- | --- |
| Limited cases and older G2 fitter | Original ten G4 identities and qualified M7 D0 |
| Candidate-dependent relative-depth affine fit | Fixed D0-anchored affine transform per image, selected once before fitting |
| No direct normal inference arm | Pinned DSINE v02 checkpoint and separate D2, D5 and fusion arms |
| Orthographic gradient proxy | Perspective backprojection at calibrated intrinsics and independently checked pixel-centre ray intersections |
| Fitting-view emphasis | Four reserved camera yaws, exact distance to triangles in both directions, existing rebind plus a crossing screen for local candidates |

## Capture and partitions

Six MakeHuman meshes reproduce the G1 and G2 recipes. Four original MB-Lab source blobs match the G2 SHA-256 records. Family B uses the same fixed one-time stature and floor alignment as G4. The fixed development partition is A_high_mass, A_muscular and B_female. Seven remaining identities are excluded from parameter selection. Numerical weights were declared before this run based on G2 and unit scaling. The matrix reports one fixed configuration. A systematic development-only hyperparameter sweep and a second independently collected evaluation cohort remain open.

Blender Workbench 4.3.2 renders 384-square native-rest captures. The 12 yaw angles comprise eight eligible acquisition views and four immutable evaluation views. Two material variants at front and lateral make 14 RGB images per subject. The frontal/lateral/rear photographs are nested into the 1/2/4/8 controls. Source image hashes and camera fields are recorded per image. Blender raster alpha agreement is evaluated against the independent numerical observation raster.

## Exact and predicted channels

The G4 camera has right, up and toward-camera normal axes. Depth is positive optical-axis Z, in centimetres. Unprojection uses the camera focal length and pixel-centre coordinates. Euclidean distance equals positive Z times the norm of the positive-forward ray for perspective. The numerical raster uses inverse-Z interpolation in perspective, linear-Z interpolation in orthographic projection, nearest surface visibility, an explicit 10–10,000 cm admitted volume, and separate background, foreground, and eroded validity masks. Exact normals are outward geometric triangle normals rotated into the right/up/toward-camera frame. Blender renders use smooth display shading. Visualization encodes values separately from FP32 measurement arrays.

Oracle fitting intersects the exact-body valid support with M7's RGB subject mask. Learned maps infer from the Blender RGB pixels before mask use. Predicted fit support uses an eroded M7 mask, finite outputs, and candidate-visible pixels. It uses no exact-body mask. The DSINE regularization path uses geometric intrinsics for the calibrated synthetic acquisitions. In-plane sign conversion is checked against the upstream depth-to-normal construction and perspective tilted-plane controls. Mono depth's affine ambiguity is estimated globally per image from D0 where both predicted and D0 surfaces are valid. It does not establish real-world physical scale.

Camera-perturbation fixtures reuse raw observations. M7 automatic registration projects weak-perspective XY and does not identify absolute camera Z. The G5 estimated path compares centered relative Z with a constructed yaw frame and uses D0 alignment. It remains a weak-perspective adaptation for predicted dense evidence. Oracle depth from calibrated views guides an upper-bound experiment even when the fit camera is perturbed.

## Fit and measurement

The no-extra comparison calls the delivered Engine B through a real project. G5's isolated copy of the product search adds per-view dense residual callbacks. The same initial state, constraints, two starts, sweep schedule and rebind gate apply to D1–D6. Depth and angular costs have separate per-image means, Huber knees of 2.5 cm and 20°, and penalize low overlap. The result records final independent dense costs, supports and product objective score. M7 combines silhouette, contour, occupancy and gap. Its landmarks participate in registration and pose. It has no independent landmark optimization residual. The bounded search budget matches candidate schedules, with minor count variation from clipping and structural fallback. Per-objective wall clocks naturally differ. A converged proof over control bounds remains open.

Canonical meshes are compared with the G2 Blender closest-triangle method using 12,000 area-weighted samples in each direction and deterministic sample seeds. No candidate receives individual realignment. The same-family direct vertex report checks known vertex identities. For cross-family measurement, the method uses the original fixed alignment and triangle surface distance. Held-out view diagnostics cover IoU, contour composite, camera Z error, normal angular error and valid pixel counts. Sections use fixed reference height planes. Per-region results are fixed approximate anatomical bands plus a front/rear split.

## Local checks

D7 and D8 diffuse and bound per-vertex normal displacement, retain vertex order and topology, and pass required product rebind before evaluation. D8 uses D0-anchored predicted depth and DSINE agreement. L0 uses an independent photographic-mask control with the same diffusion and displacement bound. New disjoint-index Blender triangle crossings trigger parent retention. The existing body may itself have crossings. Count them independently for D0–D9. The mesh snapshots contain canonical positions and triangle indices; they leave UV and skin data in the unchanged body contract. Two representative cases were exported with the M7 writer. Their D0, D7 and D8 topology, UV and skin data matched, and six Blender 4.5.16 USD import, deformation and edit/save/reopen checks passed.
