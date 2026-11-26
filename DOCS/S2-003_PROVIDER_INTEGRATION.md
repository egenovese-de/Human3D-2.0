# S2-003 — Optional anatomical provider integration
DONE for RC1 mandatory scope.
## Corrections and consumer audit
S1-005 39a9dd4368b0acdc2c4af4a231d156d146f54be2 isolates optional provider exceptions and invalid binding. d27f024fb56dd4a94b810fb64fd0aa576a558d48 adds optional programmatic PhotosWindow provider injection and shared detector factory for target/reference detection. Native default unchanged; CLI remains native. ObservationStore persists typed evidence; Session publishes photo-bound results; fusion, alignment, fitting and face consume visible_pose; alignment uses confident nonconflicting yaw; appearance propagates hidden regions; texture_bake consumes them. Garment fitting and USD export consume downstream results indirectly. 1b8f0660a931cbc21e8ee430a1c8b3614c9dbc71 adds face/torso to existing limb skin-weight filter. Mask dialog raw landmarks remain review overlays. No new external provider required.
## Verified CI
87a9a4c98a911eee6cb797368b3838d67f263439 run 45803684601 all five jobs SUCCESS; Ubuntu 49 tests 4.134s; Windows 49 tests 8.899s; clean installed 49 tests 6.020s.
ac917ea8fcad567a387726e9d4a0a927330b0026 run 45804240065 all five jobs SUCCESS; Ubuntu 50 tests 4.681s; Windows 50 tests 7.797s; clean installed 50 tests 4.621s.
f0dc4e501df380896d15e14e825e8e63792cb480 run 45809370038 all five jobs SUCCESS; Ubuntu job 139873011530 50 tests 4.412s; Windows job 139873011602 50 tests 11.744s; clean installed 50 tests 5.578s. 26 pins, zero active advisories. Actual pinned assets PASS both, frozen digest 1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650.
## Canonical hidden region mapping
| Region | Ubuntu | Windows |
|---|---:|---:|
| face | 3381 | 3381 |
| torso | 2585 | 2584 |
| left_arm | 2260 | 2260 |
| right_arm | 2260 | 2260 |
| left_leg | 2596 | 2596 |
| right_leg | 2596 | 2596 |

Both platforms PASS nonempty region, valid vertex indices, left/right limb disjointness and empty native-default exclusion. One torso vertex count difference recorded; cause unverified, threshold floating-point behavior is a hypothesis only. Exact cross-platform equality was not a gate; retain existing >0.7 threshold rather than change geometry without evidence. Counts do not establish anatomical accuracy, exact vertex-set equivalence or visual texture quality.
## Limits
Mock provider only, programmatic injection, no live VLM endpoint/credentials/configuration UI; B3-003 remains blocked. No empirical tests or pre-fix failing texture run. No actual texture quality certification. Provider timeout/cancellation remains outside this task (S3-002). AUD-01 resolved for mandatory optional-provider isolation and wiring; external service validation remains separate. S2-004 not started.
