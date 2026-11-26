# S3-001 — Reconstruction capability and GUI actions (AUD-02)
2026-11-26.
## Correction
7bef8597d963590057a9f532cdd9165ce248cfb1: Session.snapshot derives reconstruction readiness from target and frozen body reference rather than unconditional engine_unavailable.
8efe5dda391988e61b5e6a5c28eae1a9bc8a0629: desktop action registry and dynamic gating for project, target, fit, mask and revision prerequisites; refresh after guarded operations; contextual readiness status.
6452c8c498a3a5da4bcdc61e756ccf4b0f74829f and 497fcdd1b3dd83d218bda7896eb837b4905bf0be: update desktop test and convert AUD-02 characterization to regression. Real offscreen Qt button disabled on empty project and after photo ingestion without frozen reference; enabled after synthetic frozen digest registered; mocked fitting callback invoked only when enabled; export disabled without fit.
## CI
https://github.com/egenovese-de/Human3D-2.0/actions/runs/45832078193 exact head 497fcdd1b3dd83d218bda7896eb837b4905bf0be. All five jobs success: classify 139952033541, scan 139952034006, Windows 139952113373 (61 tests 8.606s; clean install 61 tests 4.694s), Ubuntu 139952113391 (61 tests 3.181s), summary 139953242965. AUD-02 regression PASS all three. Actual pinned assets PASS both; frozen digest unchanged 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650. 26 pins, zero active advisories.
## Limits
Resolved reproduced unconditional capability/status mismatch. Readiness checks registered prerequisites, not asset integrity or actual reconstruction success. Synthetic digest and mocked fit callback; no dedicated positive tests of every downstream action, no complete GUI reconstruction or empirical tests. Full synthetic GUI workflow remains S5-002; worker lifecycle remains S3-002. No redesign. S3-002 not started.
