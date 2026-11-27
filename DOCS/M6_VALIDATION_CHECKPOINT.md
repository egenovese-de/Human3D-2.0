# M6 validation checkpoint

Product candidate `1c46f93500486c9b356fa6bbfb14e6f61a942b77`. Evidence branch `f621f80e8e01f77ecad65212bed1aaf2b7e9aed9`.

## Regression and runtime

All 86 local tests passed on Linux with the locked dependencies and Python 3.11.9. The suite covers v1 observation compatibility and v2 round-trip provenance, interrupted project snapshot recovery, real-child cancellation with stale publication rejection, and target-only fit invariance. Windows and Linux locked foundation jobs, the scan and the summary passed on the same [candidate CI](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45947600959). The Windows foundation job includes clean wheel installation.

The paired local synthetic profile ran v0.2.0 and the candidate sequentially with the same frozen body, one OpenBLAS thread and the same fit/bake/export test loop. Wall time was 14.02 s and 14.96 s. Peak RSS was 261.48 and 260.67 MB respectively. Peak on-disk test artifacts were 10.01 and 10.01 MB (decimal), and the USDZs were 1,150,032 and 1,145,820 bytes. Both used the same frozen-body digest. These are a single controlled Linux pair at 256 px, with the tool's temporary directories removed on exit.

Reference tests replayed 14 cases across two Q target identities. Each utility rule accepted all four wrong-identity cases. Each accepted eight of ten same-identity cases and passed over the two redundant frontal views. This supports a limited novelty distinction. It leaves geometry/appearance identity-based selection unqualified for promotion.

## Release readiness

BLOCKED. The landmark and rig evidence gates still require independently validated semantics for landmarks and cross-rig transverse bind frames. Independent source-family confirmation of the bootstrap acceptance rule remains unavailable. The editable USDZ suite completed 4/7 historical controls before import gating. Two synthetic photograph cases still have body/garment crossings at allowed fit parameters. The independent ring garment has neutral or posed layer intersections depending on the attempted correction. The stricter collision checks remain in place.

The project has no authorized v0.3.0 promotion while these gates remain open. A reproducible development wheel can be used for smoke testing with its existing package version. The remaining work includes the end-to-end quality comparison, independent holdout regressions, and an export-safe repair for the rejected garments. See [same-commit benchmark evidence](https://github.com/egenovese-de/Human3D-2.0/tree/f621f80e8e01f77ecad65212bed1aaf2b7e9aed9/DOCS/m6).

## Paired quality and dependency replay

The full single-view photo pipeline was repeated on four Q development identities using the exact same image bytes, pose model, frozen assets, evaluator and held-out cameras. Both versions emitted body and garment USDZs in 4/4 cases. Per-case held-out IoU, symmetric posed surface residual and observed UV coverage matched exactly. Mean held-out IoU was 62.37%, mean symmetric residual was 36.61 mm, and mean observed UV coverage was 37.28% on both versions. This establishes non-regression in the tested development slice. Independent source-family validation remains open.

Excluding a reference in each of four copied projects changed the shared evidence dependency digest and hid the stale fit. The stored observations survived exclusion. Restoring the identical dependencies made the old fit reusable on reopen. Switching among targets preserved the shared body hashes.

## Blocked implementation work

- Landmark orientation and pose promotion require an independently confirmed detector landmark map and transverse bind axes. The tested confidence variant reduced held-out IoU. The schedule variants increased forearm direction error.
- Bounded regional geometry changes and automatic fit acceptance need demonstrated gains against a separate source family, including beneficial and harmful fits. The same-family direct-surface trials and fallback replay do not qualify a change.
- Facial controls need independent landmark and profile correspondence with disagreement bounds. Existing silhouette and facial texture observations do not qualify new controls.
- Identity-based reference promotion is blocked because the tested rules accept incompatible references.
- Three of the seven historical editable USDZ controls require a repair that passes the new exact collision checks.
- A v0.3.0 candidate requires the unresolved technical gates. The smoke-test wheel is the application-only build of the code revision stated above.

The [final Lab evidence tree](https://github.com/egenovese-de/Human3D-2.0/tree/cbc0802bca35d0cd1927c1984402492726ca14ac/DOCS/m6) contains the paired metrics and fixture hashes. The native-layer render was produced by direct Blender USDZ import at the same candidate. Its PNG SHA-256 is `9a9b26ffea3678dfbd83e96820f6f4cc4caf85bd3a6258a31503ea9ff1cbed50`.

The later [completion benchmark](M6_FINAL_BENCHMARK.md) supersedes this checkpoint for the latest tested code revision. Historical Q and M6 checkpoint results remain traceable.
