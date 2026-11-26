# S2-009 — USDZ portability, pose and Blender integration
2026-11-26.
## Findings and changes
0387762371fff3f5eaee9a8c26448391ec55bdc5: reject empty export mesh, unsafe garment identifiers and invalid observed coverage; check default pose authoring, archive CRC and expected texture members, reopened stage and pose matrices at frames 1 and 2.
90a3c5488392ca2c336a07bf821b5f4626762601: synthetic textured triangle, known 90-degree root rotation, relocate USDZ and remove original directory, check archive, texture resolution, expected pose and invalid garment name rejection.
Run 45827327658 reproduced Windows PermissionError WinError 5 on temporary body.usdc and asset.usdz; Ubuntu 61 tests passed, Windows 61 tests with one error. Scoped stage authoring and validation release USD references before packaging and atomic publication. Final revision aff6bcf2dbfd65d0d0ce7fbca452d8ea4e2fe533 removes incompatible out-of-scope deletion statements while retaining scoped functions.
## CI evidence
https://github.com/egenovese-de/Human3D-2.0/actions/runs/45828087705 exact head aff6bcf2dbfd65d0d0ce7fbca452d8ea4e2fe533. All five jobs success: scan 139937860652, classify 139937861209, Ubuntu 139937948307 (61 tests 2.564s), Windows 139937948322 (61 tests 8.255s; clean install 61 tests 4.414s), summary 139939087022. Portability regression PASS all three. Actual pinned assets PASS both; frozen digest unchanged 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650. 26 pins, zero active advisories.
## Limits
Windows failure reproduced after initial export hardening; no claim that all original static findings were dynamically reproduced. OpenUSD relocation fixture is not a direct Blender import or canonical multi-garment round-trip. Blender verification remains S4-005, Windows 11 client remains S1-002. No empirical tests. S2-010 not started.
