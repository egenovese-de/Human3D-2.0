# S2-010 — Observation revision invalidation (AUD-05)
2026-11-26.
## Correction
bcb2adfd72110a568b37c0eb6c185fe6be50d77b: Session dependencies include included-photo detection and correction digests and shared-fit digest; synchronize after detection, mask and fit publication, edit and restore.
c55ac479e4817c4e0657bf4496c4cbf88dd1ff7b: Coordinator.invalidate retains the newly published source artifact across generation change while invalidating other artifacts and queued/running jobs.
6093fbe35ffdba80f6c168564f13af1b0bae398a: convert AUD-05 baseline characterization to regression: persisted mask revision changes evidence digest and generation, old running preview cannot publish, previously valid preview becomes stale and remains retained, new mask current, identical mask does not advance generation.
## CI
https://github.com/egenovese-de/Human3D-2.0/actions/runs/45829440057. Head 6093fbe35ffdba80f6c168564f13af1b0bae398a. Five jobs success: scan 139942821043, classify 139942821335, Ubuntu 139942886910 (61 tests 7.281s), Windows 139942887055 (61 tests 8.418s; clean install 61 tests 4.848s), summary 139944137658. AUD-05 regression PASS all three. Actual pinned assets PASS both; frozen digest unchanged 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650. 26 pins, zero active advisories.
## Limits
Resolved reproduced same-session mask invalidation defect. Conservative global generation, not granular dependency graph. No dedicated new detection/fit revision race tests, no exhaustive cross-process publication race coverage; finish and subsequent sync are separate coordinator operations. Actual downstream stale GUI/export use was not reproduced by original probe. Full GUI and worker lifecycle remain S3; no empirical tests. S3-001 not started.
