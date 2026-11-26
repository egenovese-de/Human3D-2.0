# Human3D 2.0 stabilization candidate

2026-11-26

- Application revision `67455b36e4d586eae2d347c1f9e1a240a2e61ea0` on `development/stabilization`.
- M5 reference `a7f297806f6b2b6b2d51caa61565fbc9b2cc273a` and Lab runner `3828e922466bb53a8110114553b4aaa1c11fd758`.
- Toolchain CPython 3.11.9, the platform locks, setuptools 84.1.0, and Blender 4.5.16 LTS for the editable-file check.

## S3-005 and S4-001 · Desktop regression

The 36-switch, six-reopen Qt test checks persisted target selection, shared-fit identity, unchanged project file inventory and release of the prior session. Stale fitted previews and pose adjustments are discarded when their project revision changes. Attaching a session clears session-local pose corrections.

Before the worker cleanup fix, the two focused tests found retained progress dialogs after successful, failed and cancelled operations. Dialogs now schedule deletion after worker shutdown. The installed desktop probe exercises cleanup of the mask, appearance and garment dialogs through the GUI workflow.

The suite retains the focused regressions for stale publication, worker cancellation, interrupted persistence, job retention, asset integrity, observed UV, garment clearance and portable USD. Local regression passed 69 tests.

## S4-002 · Required CI

The stabilization push and PR suite and the manual configuration share the hash-pinned Windows/Linux foundation matrix. The legacy unlocked Foundation and M1-only Locked runtime definitions were removed from the stabilization branch. First run [45861290343](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45861290343) was rejected before starting jobs. Quoting the binary-only pip commands as YAML block scalars restored the matrix in [45861577131](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45861577131).

GitHub requires a workflow definition on the default branch for `workflow_dispatch`. The definition is currently absent from `main` at `95b5bfeb805e57f70db579ed384080679759a9e6`. Direct manual dispatch remains pending the reviewed default-branch integration. Push checks ran on the stabilization revision. See the [GitHub workflow event reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch).

## S4-003–006 · Lab, geometry and Blender

Lab used the hash-pinned four-view and studio fixture archives, the same asset bytes, detector revision and package pins from the [M5 baseline](S0-003_M5_BASELINE.md), and the full-resolution original four views. The studio archive SHA-256 is `101aa640aee4bda2ae9b77643d0f48a9a0d05c1369f7bc9905450d0a749750e4`. The four-view archive SHA-256 is `f673f4ecb9957ee0c06676a175bbbc29128655c5c582a07ae4cb2586dac709f5`. The benchmark ran from a detached local checkout at `5a8cd031333787ff40ef45d3b3e8c2b9328a461a`, whose tree matches published `ca0424db69f85e1a092e505c7625626717a637cd`. Later application changes concern dialog disposal only.

- Studio negatives 3/3 returned no subject. Positives 6/6 produced one candidate. The upper-body crop retained its insufficient-full-body-evidence flag.
- Four views fitted and exported the body and a separate textured top. The validated frozen artifact SHA-256 was `1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650`. The exported body group has 13,380 vertices and 13,378 faces. The frozen mesh has 21,334 UV coordinates, and the rig has 163 bones. Maximum body skin-weight sum error was `3.33e-16` against a `1e-4` limit.
- The canonical Lab check moved 848 jaw vertices locally, rebound the rig and verified immutable canonical topology, UVs and rig. It ran against the same frozen digest as the CI structural probe.
- Blender directly imported the candidate's garment USDZ with the body and top as separate editable meshes, packed textures, UVs, and the shared 163-bone armature. The pose action and posed deformation survived .blend save/reopen. An edit to a garment vertex survived a second save/reopen, and deleting the garment preserved the 13,380-vertex body.

| Paired measure | M5 baseline | Stabilization |
|---|---:|---:|
| Mean fitting-resolution silhouette IoU | 75.471% | 75.669% |
| Front IoU | 77.931% | 78.253% |
| Three-quarter IoU | 74.280% | 74.744% |
| Profile IoU | 72.869% | 72.773% |
| Rear IoU | 76.803% | 76.907% |
| Observed body UV fraction | 90.385% | 90.128% |
| Mean detector-landmark RMSE / silhouette height | 2.921% | 2.946% |
| Mean contour error / silhouette height | 1.437% | 1.434% |
| Top minimum sampled clearance | −0.944 mm | −0.982 mm |
| Calibrated held-out IoU | 99.672% | 99.672% |
| Calibrated vertex RMSE | 3.790 mm | 3.790 mm |

Application and Lab commands are documented in the [pinned M5 benchmark](https://github.com/egenovese-de/Human3D-2.0/blob/3828e922466bb53a8110114553b4aaa1c11fd758/DOCS/M5_FINAL_BENCHMARK.md). Both calibrated runs used `--regional --carve --independent`. The revised per-axis raster scaling in stabilization changes the fitted solution for non-square input. Small profile IoU and observed-UV decreases were observed with the paired input. The top remained within the existing 1 mm sampled tolerance, with 0.018 mm margin. The benchmark records one fixture run per revision and provides no performance or anatomical-equivalence guarantee.

## S5-001–004 · Package, install and application evidence

[Required checks 45862046396](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45862046396) passed all five jobs at the application revision. The full frozen-asset and canonical pipeline profiles also passed on both platforms.

| Validation | Result |
|---|---|
| [Ubuntu 24.04 hosted](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45862046396/job/140055508585) | 69/69 regression tests PASS (3.032 s) |
| [Windows Server 2022 hosted](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45862046396/job/140055508436) | 69/69 regression tests PASS (10.063 s) |
| Clean Windows Server 2022 candidate install | Installed the verified wheel into a fresh environment, ran native smoke and passed 69/69 tests (5.534 s) |
| Clean Linux candidate install | Installed the verified wheel in a fresh environment and passed the complete offscreen synthetic GUI probe |
| [Windows 11 x64 client](S1-002_WINDOWS_INSTALL.md) | Strict clean source install and native smoke PASS, 69/69 regression tests (7.594 s), build 26300 |

Both hosted platforms built two independent byte-identical copies of `human3d-0.1.0.dev0-py3-none-any.whl` within their platform. SHA-256 values at `SOURCE_DATE_EPOCH=1795711666` are:

| Build platform | SHA-256 |
|---|---|
| Ubuntu 24.04 and local Linux | `e7bcb09559b01be3c2bf911f171e888a7a0eb2748fabfa197aba47a5023e52ca` |
| Windows Server 2022 | `e5677e70d6c4c9929e114d94670f39f72b6fcea87bd164157a6835f39fdb15f9` |

The Linux installed GUI probe clicked through project creation, photo import, frozen body attachment, native subject inference and mask approval, shared fitting, body export, textured export, garment assembly export and project reopen. It switched target while preserving the shared fit digest and verified that no dialog remained attached after deferred deletion. OpenUSD reopened the three exports and found the separate top mesh in the outfit. UI automation supplied file-picker inputs and dismissed the dialogs. The empirical gate is `NOT_RUN`.

See the [installation and troubleshooting guide](STABILIZATION_INSTALL.md) for the candidate build, runtime assets and strict Windows 11 client probe. Use separate source assets and the model at runtime. The build logs record SHA-256 and the application/license-member check. The developer wheel remains `0.1.0.dev0`.

## S5-005 · RC1 handoff

| Field | Status |
|---|---|
| Current status | RC1 readiness BLOCKED. The development candidate is available to build from the pinned revision. |
| Test results | Automated synthetic and regression results above. Windows 11 client clean install PASS. Empirical tests `NOT_RUN`. The four-view silhouette IoU of 75.669% is below the proposed 85% target. |
| Application commit | `67455b36e4d586eae2d347c1f9e1a240a2e61ea0` |
| Next task | Review the empirical and quality gates before assigning `2.0.0rc1` or publishing release artifacts. |
