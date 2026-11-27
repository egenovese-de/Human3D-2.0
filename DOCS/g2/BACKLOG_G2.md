# G2 experimental backlog

DONE means the stated experiment executed with retained evidence. PARTIAL records the measured subset and open qualification. The scan-family gate remains open pending a suitable dataset, consent and use permissions.

| Task | Work package | Status | Execution or gap |
| --- | --- | --- | --- |
| G2-001 | G1 handoff verification | DONE | Published G1 archive SHA-256, internal checksums and exact upstream replay verified. |
| G2-002 | M6 evidence audit | DONE | Source trace and actual M6 Session run. |
| G2-003 | Dataset admission | DONE | Six A and four B admitted for controlled execution. Scan candidates assessed and withheld. |
| G2-004 | Ground-truth rendering | DONE | Four Blender views per subject, perspective variants, calibrated raster channels, masks and overlays. |
| G2-005 | Photographic baseline | DONE | M6 implementation and calibrated M6 controls scored. |
| G2-006 | Positive and negative masks | DONE | M6, seeded GrabCut, uniform RGB, probability and calibrated references measured. |
| G2-007 | Negative-space constraints | DONE | Independent ablation with shared mask, baseline and search. |
| G2-008 | Continuous contour objectives | DONE | IoU, signed occupancy, contour, SDF, and local landscapes. |
| G2-009 | Dense anatomical profiles | PARTIAL | Row-profile fits and G1 cross-sections measured. Full anatomical limb-axis normalization is open. |
| G2-010 | Anatomical region segmentation | PARTIAL | Landmark and rig-label controls measured. Specialized parsing and anatomy correspondence unresolved. |
| G2-011 | Landmark correspondence | DONE | Detector-to-rig landmark study with a matched oracle substitution. |
| G2-012 | Camera and scale sensitivity | DONE | Full perspective control, five geometry factors, translation/crop, weak perspective and M6 registration readings. |
| G2-013 | Monocular depth | DONE | Relative-depth inference, ground truth, constant-plane baseline, and downstream isolated fit. |
| G2-014 | Surface normals | PARTIAL | Depth-derived normals against calibrated mesh truth. Dedicated model and separate fitting ablation open. |
| G2-015 | Dense correspondence | PARTIAL | Exact barycentric and stereo controls. Learned correspondence and external topology mapping unexecuted. |
| G2-016 | Clothing and occlusion | PARTIAL | Controlled envelope offsets, annotated external occlusion and fitted pose control. Realistic garments and accessories unqualified. |
| G2-017 | Face, hands and feet | PARTIAL | Pixel support measured. Dedicated morphology parameter recovery open. |
| G2-018 | Viewpoint information gain | DONE | Front, side, oblique, paired and four views with matched fit. |
| G2-019 | Reference-count scaling | DONE | 2/4/8/16/30 fixed-pose oracle silhouettes and corrupted-duplicate ablations. |
| G2-020 | Visual hull | DONE | Two voxel sizes, five view counts, 3D metrics and same-four-view fit penalty. |
| G2-021 | Static stereo | DONE | Calibrated static same-pose synthetic control with texture intervention. |
| G2-022 | Confidence calibration | PARTIAL | Mask Brier, threshold bins and landmark confidence/error. Other modality calibration remains open. |
| G2-023 | Evidence fusion | PARTIAL | Robust/duplicate/occlusion factors evaluated. Region-specific calibrated covariance fusion unverified. |
| G2-024 | Anatomical observability | PARTIAL | Measured registry triage. Latent parameter and fine anatomy stability are unqualified. |
| G2-025 | Evidence sensitivity | PARTIAL | Contour, profile and oracle depth Jacobians measured. Full normal/correspondence/region Jacobians open. |
| G2-026 | Controlled photographic fitting | DONE | Matched parameterizations, E9, separate depth/correspondence/hull controls and direct oracles. |
| G2-027 | Individual evidence ablations | DONE | Negative space, mask, landmarks, depth, region oracle, pose, clothing and volume controls. |
| G2-028 | Oracle attribution | PARTIAL | Paired substitutions and G1 gap measured. Full real-photo registration attribution needs G3. |
| G2-029 | Convergence and robustness | PARTIAL | Alternate initialization, order, view perturbation, missing views and duplicates retained. Broader randomized repeatability open. |
| G2-030 | Blender comparisons | DONE | Four standardized views, torso detail, residual visualization, editable scenes and UV checks. |
| G2-031 | Runtime and dependencies | PARTIAL | CPU timings, licenses and permanent Ubuntu Lab qualification. Target Windows CPU unmeasured. |
| G2-032 | Architecture decision | DONE | Minimal justified architecture, maturity decisions and exact G3 requirements published. |
