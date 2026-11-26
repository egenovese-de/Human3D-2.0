# S1-003 — Offline asset discovery and integrity
Status IN_PROGRESS; actual upstream asset bytes not yet verified in this task.
Use explicit local paths; GUI selects model and flattened bootstrap directory manually. CLI preflight:
```
python -m human3d.asset_preflight --model /path/pose_landmarker_lite.task --assets /path/bootstrap
```
The directory contains base.obj, default.mhskel, default_weights.mhw and all 14 measure targets listed in bootstrap.py. Full preflight checks 18 files including model. --legacy-morphs allows the six torso targets to be absent as a group, matching existing freeze behavior; do not use for full M5 baseline. Exit 0 only if all required hashes match, 1 otherwise. Reports missing, unreadable and mismatched files without downloading or modifying them. Existing detector and freeze retain independent digest validation. Model Lite v1 upstream URL and digest in DEPENDENCY_CLEARANCE.md; MakeHuman paths and pinned revision in DOCS/manifests. No redistribution authorization implied.
Tests: manifest binding, synthetic valid/missing/corrupt assets with socket creation forbidden, production corruption rejection before artifact creation. Actual model initialization/inference and real bootstrap freeze not demonstrated by these synthetic tests. Existing GUI path selection unchanged. CI pending.
