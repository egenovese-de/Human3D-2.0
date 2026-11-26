# S0-001 — Audit coverage (partial; BLOCKED)

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
S0-001 cannot be marked DONE. No production code changed; no finding severity reconciled (S0-002 out of scope). Continue remaining audit before S0 completion. No empirical testing.
