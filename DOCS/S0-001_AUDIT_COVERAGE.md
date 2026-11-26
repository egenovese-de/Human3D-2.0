# S0-001 — Audit coverage (static source coverage complete; residual evidence gaps)

Pinned production: a7f297806f6b2b6b2d51caa61565fbc9b2cc273a. Pinned Lab: 3828e922466bb53a8110114553b4aaa1c11fd758.

## Coverage
Inventory: 33 Python files including __init__.py, 10 test files, 8 workflows, 2 asset manifests, 1 asset verification script.

Prior audit reports five full module reviews and four partial reviews; not independently repeated here. Structural inspection (definitions and exception paths, not full line review) performed on alignment, appearance, appearance_dialog, body_preview, face, frozen_body, fusion, garment_fit, ingestion, mask_review, originals, proportions, regional_morphs, thumbnails, vision_worker, __init__, __main__, garment_dialog, garments, mask_dialog, native_rig, observations, project, texture_bake. Remaining full source review is outstanding; do not count structural inspection as full review.

All ten test files retrieved and test definitions/assertions inspected: test_articulation, test_desktop, test_foundation, test_garments, test_ingestion, test_orchestration, test_project, test_session, test_texture_bake, test_vision. Full line review outstanding. Desktop test explicitly expects reconstruction unavailable; session tests assert reconstruct disabled initially. Vision tests cover provider binding and native retry. These are coverage observations, not confirmed defects.

Five remaining workflow files read in full: asset-integrity (M1 push/manual), blender-probe (M1 push, minimal triangle import with usd-core 25.5.1), dependency-probe (M1 candidate binary dependencies), security-screen (manual regex scan), wheel-digests (M1 candidate wheel download/hash print). Together with three previously reviewed workflows, all eight have review evidence. No workflow edits in this task.

## CI evidence
Run https://github.com/egenovese-de/Human3D-2.0/actions/runs/45769060348 at pinned production SHA: success. Both Windows Server 2022 and Ubuntu 24.04 foundation jobs succeeded, including hashed lock installation, pip check, compileall, unittest discovery and CLI version. Credential scan succeeded. No independent local tests executed. Branch protection request rejected: INVALID_ARGUMENT, HTTP 400 invalid repository path. Protection remains unverified.

## Lab evidence
Read DOCS/M5_FINAL_BENCHMARK.md at pinned Lab SHA. Reported paired IoU 75.94%, original 75.47%, UV 90.44% paired/90.39% original, landmark 3.05%/2.92%, contour 1.42%/1.44%, calibrated held-out 99.67%. Reported 29 tests and Blender 4.5.16 import/save/reopen, 163 bones. Not independently reproduced. Lab directory listing contains fixtures/smoke.usda only; referenced lab/tools and evidence artifacts not verified. lab/reports request returned 404. Dependency manifest content review, actual artifact retrieval, full production/Lab wiring review and isolated execution remain outstanding.

## Disposition
Static source review completed in subsequent iterations; residual evidence gaps remain. No production code changed; no finding severity reconciled (S0-002 out of scope). See supplemental review below. No empirical testing.

## Supplemental full source review
All 33 Python files covered cumulatively, including the five full reviews recorded in the prior audit. Subsequent full reads: ingestion, originals, thumbnails, mask_review, frozen_body, proportions, regional_morphs, appearance, face, fusion, garment_fit, vision_worker, alignment, appearance_dialog, body_preview, __init__, __main__, project, observations, bootstrap, native_rig, garment_dialog, mask_dialog, garments, texture_bake, fitting, usd_export, desktop. Prior full reviews: anatomical_evidence, vision, session, orchestration, project_store.

### Integration observations (candidates, not severity decisions)
- desktop: synchronous detector/fitting/texture calls on GUI path; pose_corrections retained by project/revision, not persisted; status text says reconstruction unavailable despite actual fit/export actions; regional controls absent from manual edit list.
- fitting: inconsistent ratios explicitly downweighted by factor .35, not silently ignored; score uses fixed transforms within optimization stages; final raw overlap guard and bounded camera refinement present.
- export: independently rechecks garment and layer sampled clearance, resolving earlier concern about fallback garment publication via this export path. Neutral rebind validated; explicit validate_pose call absent in export_body, candidate for regression review.
- native rig/bootstrap: hash-pinned inputs and finite morph checks; hierarchy cycle and index validation assumptions warrant malformed-artifact tests; hardlink publication also used by observations and originals.
- mask dialog: zero-candidate indexing relies on caller guard; full-resolution undo copies and per-candidate drafts merit resource checks.
- texture: external hidden-region suppression covers limb prefixes, not all regions; peak allocation at 2048 atlas merits measurement.
- garments: nearest centroid shortlist and sampled gaps are not exhaustive triangle collision guarantees.

### Residual gaps
Ten test files reviewed at assertion/definition level, not full line review. CI run verified at pinned M5 SHA; no new tests run. Lab report verified, raw evidence/runners not present in inspected Lab directory; branch protection unverified; full asset manifest contents not reviewed. No claim of release certification. S0-001 remains PARTIAL pending these residual reviews; no S0-002 work or production edits.
