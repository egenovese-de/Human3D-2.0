# Human3D 2.0 — Stabilization backlog

## S0 — Audit reconciliation

| ID | Task | Status |
|---|---|---|
| S0-001 | Complete pinned source, test, workflow and Lab evidence audit; record coverage gaps | DONE |
| S0-002 | Reconcile AUD-01–AUD-10, reproduce candidate defects and assign evidence-based priorities | DONE |
| S0-003 | Establish pinned M5 baseline, regression evidence and rollback reference | DONE |

## S1 — Dependencies, installation and security

| ID | Task | Status |
|---|---|---|
| S1-001 | Reconcile production/candidate dependencies and platform locks (AUD-08) | DONE |
| S1-002 | Verify clean Windows 11 installation and native library compatibility | BLOCKED |
| S1-003 | Verify model and bootstrap asset discovery, integrity and offline configuration | DONE |
| S1-004 | Resolve confirmed security, privacy and redistribution blockers | DONE |
| S1-005 | Validate dependency failure diagnostics and optional VLM isolation | DONE |

## S2 — Pipeline and integration

| ID | Task | Status |
|---|---|---|
| S2-001 | Resolve confirmed image ingestion, orientation and coordinate mapping defects | DONE |
| S2-002 | Resolve confirmed subject detection, segmentation and native failure recovery defects | DONE |
| S2-003 | Trace provider wiring and evidence consumers; correct mandatory integration defects (AUD-01) | DONE |
| S2-004 | Resolve confirmed camera, geometry and coordinate-contract defects | DONE |
| S2-005 | Verify frozen-body integrity and correct post-freeze dependency violations | DONE |
| S2-006 | Resolve confirmed neutral geometry, rig rebinding and pose integration defects | TODO |
| S2-007 | Resolve confirmed UV, texture and material integration defects | TODO |
| S2-008 | Resolve confirmed garment geometry, skinning and collision-contract defects | TODO |
| S2-009 | Resolve confirmed USDZ portability, pose and Blender import defects | TODO |
| S2-010 | Verify observation/mask revision invalidation and stale artifact promotion (AUD-05) | TODO |

## S3 — Desktop stability and resources

| ID | Task | Status |
|---|---|---|
| S3-001 | Verify reconstruction capability and mandatory GUI actions (AUD-02) | TODO |
| S3-002 | Verify worker lifecycle, subprocess cancellation, retry and error propagation (AUD-07) | TODO |
| S3-003 | Correct project persistence, atomic writes and interrupted-session recovery defects | TODO |
| S3-004 | Measure timings, peak RAM, disk and job retention; correct blocking resource defects (AUD-06) | TODO |
| S3-005 | Verify repeated target switching, project reopening and resource cleanup | TODO |

## S4 — Regression and synthetic validation

| ID | Task | Status |
|---|---|---|
| S4-001 | Add targeted regression tests for confirmed corrected defects | TODO |
| S4-002 | Correct stabilization CI coverage and locked/manual workflow scope; run regression suite (AUD-03, AUD-04, AUD-09) | TODO |
| S4-003 | Execute synthetic end-to-end and negative-input regression benchmarks in Lab | TODO |
| S4-004 | Verify canonical topology, UV, rig and skin-weight invariants | TODO |
| S4-005 | Verify direct Blender import and editable save/reopen round-trip | TODO |
| S4-006 | Compare final candidate against pinned M5 baseline and investigate regressions | TODO |

## S5 — Release Candidate 1

| ID | Task | Status |
|---|---|---|
| S5-001 | Build reproducible Windows package or wheel and assign gated RC version (AUD-10) | TODO |
| S5-002 | Verify clean candidate installation, Qt startup and complete synthetic GUI workflow | TODO |
| S5-003 | Publish local installation, configuration and troubleshooting instructions | TODO |
| S5-004 | Record final candidate revisions, artifact hashes, test results and known limitations | TODO |
| S5-005 | Finalize RC1 readiness assessment and minimal handoff | TODO |
