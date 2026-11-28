# M7 qualification report

Application revision `020fcc793e7417d6927d9e07346678e110ae9ddc` on `development/m7`. Version `0.3.0a7`. All photo-driven qualification below uses synthetic MakeHuman captures. The source is Lab commit `115cb647b63f0ff289caa221b897780a5d521920`, cropped consistently to subject 04. Controls use synthetic MakeHuman meshes and exact anchors where documented. No real-photo or physical-workstation performance is inferred.

## CI

| Workflow | Run | State | Conclusion |
| --- | --- | --- | --- |
| Required checks | [46124003528](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46124003528) | completed | success |
| M7 empirical desktop | [46124003579](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46124003579) | completed | success |

Windows. Passed native setup, launch, GUI scenarios and Blender in CI. The Project Lead's Windows 11 laptop and real photographs remain pending.

Prior Windows failures on setup and result ordering were reproduced in the logs. The application now verifies registry canonical line endings and orders attempts using a persisted publication sequence. The Windows Blender check isolates import, deformation and save/reopen from Workbench rendering. The visual Blender captures were rendered or captured in a graphical Linux session. Full job step dispositions and final artifacts are in this archive.

## Windows runner measurements

Both engines were exercised through native PySide6 using the distributed ZIP's installation. A single frontal view took 49.63 s on Engine A. Adding two complementary references and generating a target pose took 72.92 s. Engine B on that reference set with cached observations took 24.05 s. The session peaked at 593 MiB of application memory. The full per-stage measurements are in the verified Windows artifact within this archive.

## Linux CPU execution

Local runs used application revision `ce7edfef06ecfb25d91f2884a5783bb01e818d43`. The distributed revision has the identical application source tree and changes only the CI orchestrator and Blender qualification harness. The running Qt application executed the scenarios in one session. Single-photo import took 0.010 s. Additional import took 0.015 s. Showing a fresh Qt window after module import took 0.173 s. Warm project reopen took 0.352 s. Exporting two already validated assets took 0.003 s. Process-start-to-exit smoke timings, including the 0.35 s screenshot delay, are recorded separately. Peak RSS refers to the application process.

| Scenario | Result | End-to-end seconds | Peak process MiB | Project MiB | Fitting photos |
| --- | --- | ---: | ---: | ---: | ---: |
| A single frontal | complete | 48.13 | 367 | 7.0 | 1 |
| B/F complementary references, C articulated target | complete | 76.61 | 434 | 9.9 | 3 |
| G changed target, same references | complete | 8.76 | 434 | 12.6 | 3 |
| I Engine B, same references | complete | 21.96 | 736 | 16.0 | 2 |
| I/G Engine B, changed target | complete | 8.34 | 736 | 19.0 | 2 |
| H cancel | cancelled | 0.14 | 736 | 19.0 | — |
| H retry | complete | 8.42 | 736 | 21.8 | 3 |
| D unsupported target with usable references | complete | 68.56 | 764 | 23.0 | 3 |
| E unavailable optional garment | complete | 2.36 | 764 | 24.2 | 3 |

Both engines preserved the canonical digest when changing the target and reused their geometry fit. The changed reference set recalculated anatomy while prior exports remained available. The adverse target left an inspectable canonical body. Optional garment rejection preserved it. A supplementary cancellation test requested cancellation during subject detection and preserved the previous valid result. The four-import test includes a blank input and three usable references. It does not measure four distinct usable photographs. Project growth reflects saved results, with no abandoned staging directories on the exercised attempts.

## Experimental engine

Engine B ran on the same inputs and reports which views it excluded. The default path uses weak-perspective estimates and leaves physical scale unknown. Projection metrics are computed by each engine's own raster and admission path. Their values do not establish a real-photo anatomical ranking.

G1 sampled native evaluator parity had a maximum discrepancy of 0.000177 mm. G3 controlled articulated registration produced silhouette IoU 0.976 with the supplied calibration and 0.968 with a verified sector and focal prior. These are synthetic geometry-oracle controls.

## Blender roundtrip

Blender 4.5.3 imported 4 representative USDZ files. Each imported a 13,380-vertex, 13,378-face body with a UV layer, a 163-bone armature and normalized skin weights. The tests measured mesh deformation after rotating a bone, verified texture and material bindings where present, edited a vertex, saved and reopened each scene, and checked the pose action on target exports. Body-only exports establish the tested scope. Blender logs, JSON, renders and editable examples are included.
