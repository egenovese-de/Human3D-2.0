# S3-003 — Project persistence and interrupted-session recovery
2026-11-26.
## Audit and corrections
Reviewed project.py, project_store.py, originals.py, observations.py, bootstrap.py frozen publication, session reopen and existing project tests. Existing local process locks, revision CAS, fsynced temporary files, atomic snapshot replace and content-addressed hard-link publication retained.
74158065a53a1bb4c9344cfee96512e13df4f857: POSIX directory fsync after snapshot replacement, explicit staging prefix, locked recovery of abandoned snapshot staging only after valid snapshot load, reject non-object JSON.
fe58367664feb6b3e389f1816e400ce5ded06486: session reopen invokes recovery.
6442aa890afb268b7e5c67fb4f0868b71eb9059e: real child exits via os._exit(17) before replace, verifies previous snapshot, abandoned staging, reopen cleanup, unrelated file preservation and successful subsequent save. Invalid snapshot test preserves staging and rejects malformed root.
## CI
https://github.com/egenovese-de/Human3D-2.0/actions/runs/45836902201 exact head 6442aa890afb268b7e5c67fb4f0868b71eb9059e. All five jobs success: scan 139969222297, classify 139969223087, Ubuntu 139969333530 (66 tests 4.239s), Windows 139969333626 (66 tests 9.590s; clean install 66 tests 5.000s), summary 139970912275. Both new tests PASS all three. Actual pinned assets PASS both, unchanged frozen digest 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650. 26 pins, zero active advisories.
## Limitations
No automatic reconstruction of corrupted/missing committed snapshot. No portable Windows directory fsync, physical power-loss test or network filesystem certification. POSIX directory fsync failure after replace can report failure despite visible committed revision; reload before retry. Other content-addressed stores retain existing publication protocol; orphan staging/objects are not collected by this recovery. No exhaustive interruption tests across all artifact stores or cross-process reader races. No empirical tests. No S3-004 work.
