# S0-003 — Pinned M5 baseline and rollback
2026-11-26. RC1 v2 task: establish pinned M5 baseline, regression evidence and rollback reference.

## Immutable references
- Production M5 and original rollback: a7f297806f6b2b6b2d51caa61565fbc9b2cc273a (development/m5).
- Stabilization pre-S0-003 checkpoint: 82b972aca1669fecbb326fd1f5eb6ded1f649ee1.
- Last full stabilization CI: 3605574180724486b3eae7183a00c3f17115165d.
- Lab: 3828e922466bb53a8110114553b4aaa1c11fd758 (lab/render).
- Main: 95b5bfeb805e57f70db579ed384080679759a9e6 (unchanged).
GitHub compare M5...82b972a: ahead 8, behind 0, merge base M5. Exactly five changed paths: .github/workflows/required-checks.yml, DOCS/BACKLOG_S.md, DOCS/FINDINGS_RECONCILIATION.md, DOCS/S0-001_AUDIT_COVERAGE.md, tests/test_audit_s0_002.py. No application, lock or asset changes. Branch listing reports protected=false for all four branches; detailed ruleset enforcement not independently verified. No protection changes authorized.

## Runtime identity
Git blob IDs (not SHA256):
- pyproject.toml: 253abcf534dd707fa2d457830878d29c074f26fb
- requirements-linux.lock: 669b70ab9cb19bf5088ce255a63274647d6f75e7
- requirements-windows.lock: 012149d4b98b71acdf8e21cd99787dc35422d2a7
- DOCS/manifests/makehuman-v1.3.0.json: 44f6940648b4f50e1b88484aba1aea974bf00584
- DOCS/manifests/makehuman-morph02.json: b25e4dd88149cd009992ecb5f6ef3a4857155f4b
Pose Landmarker Lite v1 SHA256 59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a (Lab report; actual model bytes not retrieved).

## Verified regression evidence
| Revision | Run | Windows | Linux | Result |
|---|---|---|---|---|
| M5 a7f2978 | 45769060348 | job 139737060992: 29 tests, 2.073s | job 139737061035: 29 tests, 0.355s | 5/5 jobs success |
| stabilization 3605574 | 45782444153 | job 139780983945: 34 tests, 3.618s | job 139780983979: 34 tests, 1.843s | 5/5 jobs success |
| stabilization 82b972a | 45783032261 | documentation-only | documentation-only | success |
Run 45783012133 (b5fed88) cancelled by subsequent commit; not a failure or a pass. Logs for original M5 and diagnostic runs inspected. The additional five tests characterize known defects; replace their expectations as fixes land. Test durations are not performance benchmarks.

## Lab reference (reported, not independently rerun)
Source DOCS/M5_FINAL_BENCHMARK.md at pinned Lab SHA. Four-view archive SHA256 f673f4ecb9957ee0c06676a175bbbc29128655c5c582a07ae4cb2586dac709f5. Paired resized M4/M5 IoU 54.99/75.94%, M5 originals 75.47%; observed UV 90.44/90.39% (paired/original); landmark 3.05/2.92%; contour 1.42/1.44%. Calibrated held-out IoU 99.67%, vertex RMSE 3.790mm, hull 95.89%. 3/3 negatives, 6/6 positives; separate body/top, 163 bones, Blender 4.5.16 save/reopen reported. Raw evidence, wheel and meshes not independently retrieved. Historical M4 values not reproduced; compare only matched protocol. B3-003 real VLM blocked. S4-003–006 must rerun synthetic evidence and compare matched fixtures, versions and metrics; unavailable raw evidence is not a PASS. No empirical testing.

## Rollback procedure (reference only; not executed)
Use the immutable M5 SHA for original code recovery and 82b972a for the pre-S0-003 stabilization checkpoint including CI and diagnostics. In an authorized local checkout: git fetch origin; git show --no-patch a7f297806f6b2b6b2d51caa61565fbc9b2cc273a; git switch --detach a7f297806f6b2b6b2d51caa61565fbc9b2cc273a. Use an isolated working directory and fresh environment with the pinned platform lock. Preserve project data separately; do not assume backward-compatible project schema. For shared stabilization history prefer reviewed revert commits of offending changes, retaining CI and audit records; no force push/reset, no automatic merge, no branch creation. Actual local checkout remains blocked by DNS; no rollback execution claimed.

## Acceptance
Pinned baseline, source comparison, verified CI evidence and rollback reference established. S0-003 DONE for reference deliverable, not RC1 certification. No application changes, no empirical test, no S1 work. Final documentation-only CI to be checked separately.
