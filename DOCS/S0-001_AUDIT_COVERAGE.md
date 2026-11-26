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

## Final residual review — 2026-11-26
All ten pinned test files now read in full: foundation (1), project (5), ingestion (1), orchestration (3), desktop (1), vision (8), session (3), texture_bake (2), articulation (4), garments (1): 29 test methods. Desktop only covers import/select/reopen; native retry and provider tests use mocks; coordinator cancellation tests publication, not native process termination. Session tests cover stale target and persisted observations, not full repeated fitting/resource stress. Articulation covers rear/profile, wrist bounds, bone lengths and collapsed faces; garment test covers signed triangle distance only; texture tests cover observed seams and occlusion. No new execution; historical pinned CI success retained.

Both manifests parsed in full: 357 + 10 entries, no duplicate paths within either manifest, all SHA-256 strings valid, positive integer byte counts, no '..' path strings. Both declare CC0-1.0 and upstream revision 1f508f6083b2f823dab15de924b3bde72e08d77c. All 17 bootstrap hash constants match manifest entries by filename and digest. tools/verify_upstream_assets.py checks pinned revision, path safety, exact size and SHA-256 against upstream bytes; not executed here. Manifest consistency is not independent asset integrity or license clearance.

Lab correction: runners reside in root tools/, not lab/tools/ as stated in report. Nine benchmark/diagnostic scripts read in full at pinned Lab SHA: benchmark_native, benchmark_geometry, check_geometry_invariants, check_supported_garments, check_usd_pose, check_visual_hull, diagnose_native, export_calibrated_geometry, lab_render_usd. Native runner checks clean product/Lab git revisions, PYTHONPATH checkout, input hashes and records simulated evidence mode; geometry runner excludes 130-degree held-out mask from fitting, supports independent analytic displacement and records metrics. Diagnostics validate pose and bone lengths; Blender roundtrip verifies armature/action and deformation, but max deformation across meshes does not prove every mesh deforms. Garment diagnostic prints sampled clearance rather than asserting zero violations. Render is visual smoke only. Geometry runner does not independently enforce product import path as native runner does. Reported metrics remain historical, not reproduced.

Evidence availability: pinned Lab root evidence/ and build/ return 404; lab/fixtures contains smoke.usda only. Repository-wide Actions artifact endpoint rejected by connector (400). Pinned production CI run artifact listing: []. Raw benchmark JSON, image manifests, USD/Blender output and wheel not independently retrieved. Branch protection remains unverified. These are explicitly recorded coverage gaps, not PASS claims. No empirical tests, no production changes, no severity reconciliation. S0-001 audit coverage deliverable complete with documented gaps; RC1 remains uncertified. Subsequent execution and evidence recovery belong to applicable stabilization gates. Earlier residual-review statements above are historical and superseded by this section.
