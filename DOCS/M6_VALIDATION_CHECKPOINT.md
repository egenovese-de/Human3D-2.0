# M6 validation checkpoint

Product candidate `1c46f93500486c9b356fa6bbfb14e6f61a942b77`. Evidence branch `f621f80e8e01f77ecad65212bed1aaf2b7e9aed9`.

## Regression and runtime

All 86 local tests passed on Linux with the locked dependencies and Python 3.11.9. The suite covers v1 observation compatibility and v2 round-trip provenance, interrupted project snapshot recovery, real-child cancellation with stale publication rejection, and target-only fit invariance. Windows and Linux locked foundation jobs, the scan and the summary passed on the same [candidate CI](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45947600959). The Windows foundation job includes clean wheel installation.

The paired local synthetic profile ran v0.2.0 and the candidate sequentially with the same frozen body, one OpenBLAS thread and the same fit/bake/export test loop. Wall time was 14.02 s and 14.96 s. Peak RSS was 261.48 and 260.67 MB respectively. Peak on-disk test artifacts were 10.01 and 10.01 MB (decimal), and the USDZs were 1,150,032 and 1,145,820 bytes. Both used the same frozen-body digest. These are a single controlled Linux pair at 256 px, with the tool's temporary directories removed on exit.

Reference tests replayed 14 cases across two Q target identities. Each utility rule accepted all four wrong-identity cases. Each accepted eight of ten same-identity cases and passed over the two redundant frontal views. This supports a limited novelty distinction. It leaves geometry/appearance identity-based selection unqualified for promotion.

## Release readiness

BLOCKED. The landmark and rig evidence gates still require independently validated semantics for landmarks and cross-rig transverse bind frames. Independent source-family confirmation of the bootstrap acceptance rule remains unavailable. The editable USDZ suite completed 4/7 historical controls before import gating. Two synthetic photograph cases still have body/garment crossings at allowed fit parameters. The independent ring garment has neutral or posed layer intersections depending on the attempted correction. The stricter collision checks remain in place.

The project has no authorized v0.3.0 promotion while these gates remain open. A reproducible development wheel can be used for smoke testing with its existing package version. The remaining work includes the end-to-end quality comparison, independent holdout regressions, and an export-safe repair for the rejected garments. See [same-commit benchmark evidence](https://github.com/egenovese-de/Human3D-2.0/tree/f621f80e8e01f77ecad65212bed1aaf2b7e9aed9/DOCS/m6).
