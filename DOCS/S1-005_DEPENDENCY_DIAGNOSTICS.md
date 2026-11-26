# S1-005 — Dependency failure diagnostics and optional VLM isolation
Status: DONE (CLI and optional adapter scope).
## Changes
39a9dd4: optional provider exceptions and invalid bindings fall back to native evidence with warning containing exception type only.
da59aea: CLI operation imports moved inside error boundaries.
fd76e82, d0f01e5: updated AUD-01 probe and added eight simulated import/native load failure cases across four CLI operations.
3d8eec5: mismatched evidence regression now verifies native result preservation and warning; valid evidence still accepted and ambiguous detections bypass provider.
## Evidence
Run 45798826303 at d0f01e5: both platforms 40/41 PASS; outdated mismatch exception expectation failed.
Final run 45799503774 at 3d8eec53e570ba7896b47af4112aa45f7b7cd79d: all five jobs PASS.
Windows job 139838842021: 41 tests in 8.123s, installed suite 41 in 4.262s.
Ubuntu job 139838842071: 41 tests in 3.108s; 26 pins, zero active PyPI advisories; wheel and license PASS.
Scan job 139838720343: 197 reachable trees and commits screened for prohibited paths and specified credential patterns.
Both platforms actual pinned assets PASS, frozen digest 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650.
## Limits
Provider failures and missing dependencies are simulated; no live VLM, provider timeout isolation, complete GUI diagnostics or Windows 11 client validation claimed. AUD-01 provider wiring remains for S2-003. S1-002 remains BLOCKED. No empirical tests. S2-001 not started.
