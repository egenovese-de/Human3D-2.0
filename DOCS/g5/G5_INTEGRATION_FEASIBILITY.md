# G5 integration feasibility

Engine B is dispatched through the M7 reconstruction service. The photographic observations are cached at source digest. The Engine B canonical cache includes observation digest, calibration content and app revision, while target selection is absent from the shared-canonical identity. The fit already retains camera provenance and a validity failure gate. A new channel would attach before registration and anatomical fitting, with fit-dependent relative-depth alignment placed after the initial contour fit.

| Area | Change class | Implementation implication |
| --- | --- | --- |
| Immutable request, target selection, prior result recovery and service staging | Reuse without modification | Evidence creation remains owned by reconstruction and publication remains atomic. |
| Source RGB extraction and normalization | Minor extension | Record oriented bytes and reversible resize, crop, letterbox and intrinsics mapping. |
| Model provisioning and CPU worker | New component | Pin source, weight hash, runtime provider, compatibility and exact rights. Support verified offline assets and worker termination. |
| Typed evidence and cache | New component | Include source, checkpoint, coordinate and validity metadata. A separate aligned cache depends on D0, camera and optimizer configuration. |
| Camera and pose adapters | Significant adaptation | Add a reliable Z and normal frame, preserve scale uncertainty and preserve posed visibility. Reject poorly registered depth/normal views. |
| Visibility and garment attribution | Significant adaptation | Separate body, garment, external occluder and evidence-unknown masks. Include lower-confidence boundary handling. |
| Anatomical fit and fallback | Significant adaptation | Maintain bounded controls and report each geometric loss. Preserve D0 if the combined path fails a qualification gate. |
| Persistence, diagnostics and evidence export | Minor extension | Persist per-view channel statistics and reasons for abstention. Keep evidence files opt-in for export. |
| Cancellation | Minor extension | Use existing cancellation-aware worker pattern. Check each frame, provider call and fitting budget. |
| Windows installer and lock | Significant adaptation | Cross-check provider wheels and CPython ABI, package or provision separately licensed assets, qualify clean installs and offline inference. |
| Future reconstruction inspector | Minor extension | Reuse stage timings and canonical snapshots, keep optional evidence and paired loss diagnostics. |
| Local deformation rig export | Significant adaptation | Add canonical rebind, topology and collision gates, pose validation and export round-trip control. |

Effort is an engineering estimate. A bounded depth-only pilot would take approximately 5–9 engineer-days. Normals alone would take 8–14, including source and model-rights resolution and a CPU deployment path. Combined evidence would take 10–18. Adding a safe local refinement path would raise the estimate to 15–25. These estimates assume usable camera and body attribution. Acquisition or pose redesign would require separate effort.
