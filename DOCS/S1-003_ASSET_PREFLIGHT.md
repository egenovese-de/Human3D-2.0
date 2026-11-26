# S1-003 — Offline asset discovery and integrity
Status DONE; actual pinned upstream asset bytes verified on both hosted platforms.
Use explicit local paths; GUI selects model and flattened bootstrap directory manually. CLI preflight:
```
python -m human3d.asset_preflight --model /path/pose_landmarker_lite.task --assets /path/bootstrap
```
The directory contains base.obj, default.mhskel, default_weights.mhw and all 14 measure targets listed in bootstrap.py. Full preflight checks 18 files including model. --legacy-morphs allows the six torso targets to be absent as a group, matching existing freeze behavior; do not use for full M5 baseline. Exit 0 only if all required hashes match, 1 otherwise. Reports missing, unreadable and mismatched files without downloading or modifying them. Existing detector and freeze retain independent digest validation. Model Lite v1 upstream URL and digest in DEPENDENCY_CLEARANCE.md; MakeHuman paths and pinned revision in DOCS/manifests. No redistribution authorization implied.
Tests: manifest binding, synthetic valid/missing/corrupt assets with socket creation forbidden, production corruption rejection before artifact creation. Actual model initialization/inference and real bootstrap freeze not demonstrated by these synthetic tests. Existing GUI path selection unchanged. CI pending.

## Final verified evidence
Run 45786267222 at b57d6e462fe88b6a723da8d93379404e22591fa6: all five jobs successful. Windows job 139796216037: 40 tests in 14.252s, isolated installation 40 tests in 4.371s; Linux job 139796216055: 40 tests in 4.813s. All three new tests passed in all three executions. Both actual asset probes passed, including 18 digest checks, detector wrapper construction and full 14-morph freeze. Identical frozen artifact SHA256 on both platforms: 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650. No corrections required. This verifies the neutral artifact, not full reconstruction. Socket patch is Python-level only; native inference and OS-level network isolation not tested. S1-002 remains BLOCKED; no S1-004 work.
