# M6 verification and acceptance

Compare pinned v0.2.0 and candidate under identical inputs, alignment, evaluation cameras, hardware and budgets. Preserve Q historical reports and separate independent identity/source-family holdouts from development data. Report sample sizes, per-subject paired effects, failures, uncertainty and runtime; no population claims from correlated variants. No empirical acceptance gate in backlog.

| Gate | Q baseline / required verification |
|---|---|
| Collision | Detect all eight known false-clear posed cases (34 intersecting triangle pairs each); independently labeled separated/touching/intersecting/coplanar controls, false positives, neutral/posed/layered checks and runtime. |
| Vision | Replay eight clean profiles and 132 stress conditions; recover useful masks without additional false automatic pose accepts on controls. |
| Evidence | Replay 27 boundary checks; v1 migration, offline fallback, typed field validation, per-field consumer effects, scale/uncertainty and conflict tests. |
| Rig | Signed three-axis rotation and bind-frame closure, independently validated landmarks, local/global geodesic errors, joint mm, contact; historical 27.82° is conditional on old mapping, rebaseline before comparison. |
| Pose/camera | Fixed geometry and evaluation camera; direction control 61.84→68.84% is an oracle sensitivity, not a promised gain. Compare native versus candidate angular, depth, joint and held-out metrics; no compensating shape changes. |
| Geometry | Registered residual 23.40 mm; compare symmetric mean/p95, regional circumferences, saturation, held-out IoU and runtime at fixed alignment. Require measured paired improvement before promoting new defaults. |
| Fit acceptance | Independent evaluation with beneficial/harmful/negligible cases; separate neutral surface and silhouette labels; frozen thresholds, false accept/reject, p50/p95 overhead. If insufficient evidence, retain default. |
| Face | Independent annotations with disagreement bounds; feature mm, profile, region/control response; no likeness claim from texture. |
| Texture | Replay 0/1/3 px and occluder controls; baseline RGB MAE 1.80 vs 32.66 at 3 px; report seam, leakage and coverage jointly. |
| References | Four incompatible inputs previously accepted; compare wrong-identity acceptance and valid-reference rejection, geometry and appearance metrics and latency on independent identities. |
| Structural | Canonical topology/UV invariance, finite vertices, valid faces, skin weight sum tolerance 1e-4, no stale promotion, target-only shared digest invariant, cancellation and migration. |
| Regression | Existing 69 tests remain passing (or explicitly mapped equivalent tests); new tests for all changes; full Windows/Linux locked CI, clean Windows installation, GUI smoke without redesign. |
| Export | Replay seven Blender round-trips; direct USDZ import, editable body/garments, pose, shared rig, save/reopen and safe garment removal. |

No universal IoU target or arbitrary runtime limit. Predeclare candidate-specific acceptance thresholds from development data before held-out evaluation. A negative experiment may complete an investigation but does not authorize a worse production default. Mandatory safety/structural failures block release readiness. Publish exact SHAs, dependency/asset hashes, scripts, machine-readable metrics and actual Blender renders. No automatic merge/tag/release.
