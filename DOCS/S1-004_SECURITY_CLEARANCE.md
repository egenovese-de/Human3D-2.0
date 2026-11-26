# S1-004 — Security and redistribution boundary
Status IN_PROGRESS. Candidate-only scope: original Apache-2.0 application wheel; no bundled dependencies, models, MakeHuman assets or Blender. Existing redistribution HOLD for third-party model remains. No binary release authorized.
 
## Controls
- Existing required checks scan reachable history for specified credential patterns; not a comprehensive secret scanner.
- New candidate ancestor tree filename screening and application-only wheel member inspection. Filename screening is not content-based personal-data detection; gitignore is advisory and can be bypassed.
- Current PyPI per-version advisory metadata for production locks and pinned setuptools; fail on active advisory or unavailable metadata. Does not cover native bundled components, OS libraries or all vulnerabilities.
- Dependency license metadata logged for review, not legal clearance. Preserve upstream notices; no third-party wheels redistributed. PySide6 LGPL/GPL and native dependencies require separate clearance if bundled. Model-specific redistribution remains HOLD.
- Local photographs, masks, textures, project JSON and exported geometry may contain personal data. Keep projects outside checkout, do not upload to CI, use OS access controls and encrypted storage where appropriate. Original bytes can include EXIF metadata. Exports may identify the subject. Delete project and export copies separately; no secure deletion claim. Obtain appropriate permission for processing and sharing. No telemetry or external provider authorization implied.
- Actual asset provisioning in CI uses public pinned upstream bytes, not personal inputs.
 
## Evidence
S1-003 run 45786267222 verified all 18 runtime assets on both platforms. New security and wheel checks pending CI. Historical license register remains authoritative for HOLD items. No legal opinion, complete native CVE inventory, or per-file authorship certification claimed.

## First security gate result (2026-11-26)
Run 45789350491, Linux job 139804262007: 40 tests PASS, actual assets PASS, advisory gate FAIL. 26 distinct pins reviewed, 25 runtime pins no active PyPI advisories, setuptools 75.8.2 five active advisory IDs: GHSA-5rjg-fvgr-3xxf, PYSEC-2025-49, PYSEC-2026-3447, GHSA-h35f-9h28-mq5c, GHSA-xmj3-9gf7-h52w. IDs may overlap. Scan job 139804158888 passed 183 reachable commits for specified patterns. Wheel inspection not reached. Qt packages report LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; usd-core reports LicenseRef-TOST-1.0; NumPy metadata includes OpenBLAS, LAPACK and GCC runtime exception terms. No bundled dependency clearance inferred. Build pin changed to candidate setuptools 82.0.1 (425a327560bfec486863f27496480654dacfccf0); audit now reads actual build-system pins (c7a538e54e8e34007f12054bd04a5c99599494be). Candidate security and build compatibility pending fresh CI; no advisory waiver. S1-004 remains IN_PROGRESS; S1-002 BLOCKED.
