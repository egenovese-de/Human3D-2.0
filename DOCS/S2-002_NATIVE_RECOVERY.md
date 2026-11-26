# S2-002 — Subject detection, segmentation and native failure recovery
Status: DONE within tested scope.
## Changes
bffb33ed2978cf2cb242beab37d123ba30ce2fd0: normalize subprocess launch OSError and invalid/missing/unreadable observation results to retryable RuntimeError; reject nonpositive or oversized mask content dimensions.
15f892a5cc5cb03999ebb4504c2b5233b2a6ec7a: tests/test_native_recovery.py covers simulated launch failure, timeout, malformed stdout, missing artifact, nonzero exit, successful retry after each, photo digest mismatch, invalid mask dimensions, nonfinite/out-of-range probabilities, empty/full masks and valid mask.
## Evidence
Run 45802447078 (production-only commit) cancelled; superseding run 45802467891 at 15f892a completed SUCCESS, all five jobs.
Ubuntu job 139849031909: 47 tests in 4.130s; 26 pins, zero active advisories.
Windows job 139849032087: 47 tests in 9.093s; installed suite 47 tests in 11.251s.
Both new test methods passed in all three executions. Both actual pinned asset probes PASS, frozen digest 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650.
## Limits
Defects identified by source inspection; no pre-fix failing run recorded. Subprocess failures are mocked, not actual native crashes/timeouts. No empirical detection accuracy or segmentation quality validation, no GUI cancellation/lifecycle certification (S3-002). Windows 11 client remains unverified (S1-002 BLOCKED). No changes to model or VLM wiring. S2-003 not started.
