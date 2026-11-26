# S2-005 — Frozen body integrity
Date: 2026-11-26. Targeted stabilization scope complete.
## Changes
- dcba812cede6ba0706cde79e6103bc7d9753b4ef: validate hash-addressed frozen body structure at load boundary: finite vertex/UV/joint vectors, face references, bone head/tail and parent hierarchy, skin count and normalized nonempty weights, joint bindings and morph indices/finite offsets. Empty skin influences remain permitted for compatibility.
- 2164102e28a2257239d79297b946680d45862e65: canonical asset verification uses production loader.
- 38066de947e2a3dfb2552519f6c0735294b85e9a: valid fixture, corrupted bytes and seven hash-valid malformed fixtures.
- 25b0bd7dd525739bc6f1db21c297470353bffc56: include frozen body digest in coordinator dependencies.
- a457eacf3947c3b7a310657a98ed2717f646d757: regression verifies previous preview becomes stale after frozen binding changes.
- 510caf7c519fcda8084a7c5538a466d84e36f642: actual canonical morph deformation, validate_rebind, compare full original in-memory body, repeat freeze, compare original bytes and reload.
## Contract review
Bootstrap verifies source assets, writes deterministic JSON, publishes via hard link without overwriting, checks existing bytes. Explicit project rebinding remains supported; individual artifacts remain content-addressed. Session shared fit checks bootstrap/evidence/current fit before publishing; current and restorable fits check bootstrap and evidence. Desktop preview is revision-keyed. Deformation copies neutral vertices. Coordinator now invalidates on frozen binding changes. Observation/mask invalidation remains S2-010. Rig/pose, texture and garment integration remain their respective subsequent tasks.
## Verified CI
Run 45812370331 at 38066de: all five jobs success; Ubuntu 55 tests 3.990s, Windows 55 tests 8.251s, clean install 55 tests 4.936s; canonical structure PASS both.
Run 45813304011 at a457eac: all five jobs success; Ubuntu 56 tests 8.170s, Windows 56 tests 8.832s, clean install 56 tests 4.998s; frozen binding invalidation test PASS all three.
Final run https://github.com/egenovese-de/Human3D-2.0/actions/runs/45814289306 at exact head 510caf7c519fcda8084a7c5538a466d84e36f642: all five jobs SUCCESS. classify 139889866563, scan 139889866923, Windows 139889966288 (56 tests 11.173s; clean install 56 tests 4.543s), Ubuntu 139889966296 (56 tests 4.038s), summary 139891109591. Both platforms logged Canonical frozen structure: PASS and Canonical post-freeze deformation/rebind and repeat freeze immutability: PASS. Actual pinned assets PASS; unchanged digest 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650. 26 pins reviewed, zero active advisories.
## Limits
Static identification of defects, no executed pre-fix reproduction. Structural validation is not exhaustive geometry/rig certification. Canonical immutability probe covers morph deformation, rebind validation and repeated freeze, not every downstream operation. No empirical tests or Windows 11 client certification. No additional tests added after final successful CI. S2-006 not started.
