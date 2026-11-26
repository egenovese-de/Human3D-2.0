# S3-002 — Worker lifecycle (AUD-07)
2026-11-26.
## Corrections
a85af5f: cancellable Popen runner, 100 ms polling, kill and communicate on cancellation/timeout; detector close signals cancellation.
a04c6f5: modal Qt progress and background thread for detection, shared/target fitting, atlas baking and plain USD export.
4cbc804 and 8bc0f15: cancellation check at Session publication boundary and adapter forwarding.
d57b873: textured and garment USD export off GUI thread.
ce17d93 and ebb77cd: garment fitting and export preparation dispatched to worker; progress dialog rejects close/Escape until worker completes.
adb89c0, 5853cb2, 87c88e5, 6a9ace3, aa8c6b8: regression probes and native recovery mocks.
## Verified CI
https://github.com/egenovese-de/Human3D-2.0/actions/runs/45835389917 exact head aa8c6b8ce0b8275e0cc57f5cfeb71e933025269d. All five jobs success: classify 139964330149, scan 139964330606, Windows 139964443081 (64 tests 8.588s; clean install 64 tests 3.575s), Ubuntu 139964443266 (64 tests 3.546s), summary 139965641548. AUD-07 synthetic child cancellation, Qt timer/error, cancel dialog cleanup and garment worker dispatch tests passed. Actual pinned assets PASS both, unchanged frozen digest 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650. 26 pins, zero active advisories.
## Scope and limitations
The reproduced logical-only native cancellation and main heavy-path GUI blocking defects are corrected. Cancellation probe uses a substituted sleeping child and explicit coordinator cancellation, not actual native inference or end-to-end session cancellation. Garment dispatch uses mocked export preparation. Qt responsiveness probe uses synthetic work. Python numerical work is not preemptible; optional external provider may block; secondary preview and other synchronous preparation paths are not exhaustively certified. Cancellation check and publication are not atomic against a late event. No process-tree termination guarantee beyond direct child. Full synthetic GUI workflow remains S5-002; no empirical tests. No S3-003 work.
