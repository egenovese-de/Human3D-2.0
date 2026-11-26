# S2-006 — Neutral geometry, rig rebinding and pose integration
2026-11-26. Targeted stabilization.
## Findings and changes
- 33569aee96ba5d3a0d1fcdbc256d450f13a1fb1f: reject nonfinite limb angles, depth ratios and wrist axes before pose solving; validate finite neutral vertices and reject missing body triangles in validate_pose.
- 1d071b1fc0cb35c6a882d18c26444bff4ef91f79: export_body always computes posed vertices and validates pose before writing output, including plain OpenUSD.
- 119960e76fbe413455b31c8f804987e365c48680: move manual preview pose computation and skinning inside ValueError handling.
- 75cbaf541e9dbaddb9bbeafc9bd3fa8404257ca3: two regression methods in tests/test_pose_contract.py; independent expected 90-degree rotation, nonfinite parameters, collapsed face, nonfinite neutral and missing topology.
## Verified evidence
https://github.com/egenovese-de/Human3D-2.0/actions/runs/45815338197 exact head 75cbaf541e9dbaddb9bbeafc9bd3fa8404257ca3. All five jobs success: scan 139894848067, classify 139894848421, Ubuntu 139894903240 (58 tests 3.231s), Windows 139894903503 (58 tests 8.842s; clean install 58 tests 4.800s), summary 139896230003. Both new methods PASS in all three configurations. Canonical deformation/rebind/repeat freeze immutability PASS both platforms; unchanged digest 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650. 26 pins reviewed, zero active advisories.
## Limits
Defects identified statically; no executed pre-fix reproduction. New tests directly cover core pose contracts, not dedicated GUI correction or export rejection integration probes. No exhaustive self-intersection, extreme pose, rig hierarchy or anatomical accuracy certification. Canonical rebind probe inherited from S2-005. Blender round trip and broader synthetic benchmarks remain subsequent tasks. No empirical tests. S2-007 not started.
