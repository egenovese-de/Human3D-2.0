# Human3D 2.0 — M6 architecture baseline

Baseline: v0.2.0 / 480195f05fb2d1ed6c71dceabf4ba54b8bed69db. Q closure: bc351c9. Target v0.3.0 (publication requires approval).

## Architecture decisions
Preserve presentation/application/reconstruction separation, immutable frozen canonical assets, revisioned project storage and dependency-aware invalidation. GUI design remains frozen; only compatibility and functional regression fixes are permitted. Preserve offline CPU operation on Windows 11 and Linux. No mandatory VLM, GPU or network dependency.

### Evidence v2
Version the photo-bound evidence contract. Preserve v1 readers and offline fallback. Typed observations carry photo digest, candidate, provider/model/schema provenance, region, semantic definition, coordinate frame, units, value or interval, uncertainty, visibility and calibration reference. Unknown is distinct from zero. Support relative proportions, regional circumferences and volume proxies, morphology, asymmetry and continuous visibility. Absolute metric values require independently justified scale calibration; otherwise use dimensionless ratios or explicitly uncertain estimates. Never infer hidden anatomy as observed truth. Validate finite values, ranges, units, conflicts and stale bindings. Each accepted field must have a documented consumer and known-effect test; unsupported fields must not silently influence fitting. Confidence is not a calibrated probability unless validated. Fuse correlated observations conservatively, preserve provenance and reject contradictory scale assumptions. Keep v1 compatibility and deterministic provider fixtures; actual external provider evaluation remains optional when credentials are absent.

### Vision and reference evidence
Separate mask suitability, landmark suitability, pose suitability and identity compatibility. A useful lateral silhouette may contribute to geometry without authorizing an unreliable pose. Preserve review for ambiguous, cropped or misidentified subjects. Maintain separate geometry and appearance reference selections, with target pose tied to the selected photograph. Identity-aware filtering must be validated before automatic rejection; uncertain cases retain review. No mandatory identity service.

### Rig and registration
Define canonical axes, handedness, units, bind matrices, parent-relative transforms, joint centers versus surface landmarks, local/global rotations and twist conventions. Validate signed rotations on three axes, source and target chain closure, axial twist, wrist/foot frames and spine/pelvis. Use independent landmark annotations with uncertainty and visibility. Never equate segment direction with full rotation. Registration and experimental surface transfer must preserve correspondence quality; reject invalid face areas and report transfer residual. Do not silently repair independent truth into a canonical control.

### Pose, camera and geometry
Keep neutral shared anatomy independent of target pose. Establish fixed-geometry pose/camera calibration before changing estimation order. Evaluate direction, depth, full rotations, contact and camera compensation separately. Use bounded optimization, calibrated confidence and explicit missing observations. Compare pose-first and alternating schedules before selecting one. Preserve canonical topology, UVs, skeleton and skin contracts by default; alternative bases are Lab experiments until compatibility and independent gains are established. No topology replacement or incompatible project format without explicit architectural approval; continue compatible work meanwhile.

Fit candidates are immutable revisions. Evaluate regional residuals, cross-view consistency, saturation, plausibility and validation-view evidence where available. Keep previous accepted geometry available. Ground truth is evaluation-only; no hidden oracle in production. Separate neutral shape quality from posed silhouette utility. Calibrate acceptance rules on development identities and evaluate on separate identities containing beneficial and harmful outcomes. If validation is insufficient, keep existing default and expose only internal experimental diagnostics. Target switching must not change shared anatomy without a genuine dependency change.

### Texture, face and garments
Guard texture projection with camera/pose alignment and visibility; measure color error separately from UV coverage. Preserve unobserved provenance. Add facial controls only when independently annotated benchmarks support them; preserve topology and skinning. Triangle-level garment validation uses broad-phase acceleration and robust narrow-phase intersection tests, explicit adjacency/contact/coplanarity tolerances, neutral and posed checks and layer-aware diagnostics. Do not claim collision freedom from sampled clearance. Do not invent volume for open/self-intersecting shells; material volume requires thickness. Reject or flag invalid outputs rather than silently declaring success; any automatic correction must be separately verified.

### Persistence and export
Evidence, rig convention, geometry and reference-policy revisions participate in dependency digests. Migrate existing projects without data loss; preserve rollback and cancellation/stale-result guards. Export separate editable body/garments, UV/materials, shared rig and target pose via USDZ; verify direct Blender import, deformation, edit/save/reopen and garment removal. No implicit MakeHuman invocation after freeze.

## Architecture checkpoints
Record baseline decisions before implementation, review after rig/evidence contracts and after integrated validation. Keep detailed decisions outside backlog. Incompatible changes require Project Lead approval; do not block independent work. No GUI redesign until M7.
