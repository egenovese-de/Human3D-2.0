# M6 completion benchmark

Product code `b2a84312ccf2d2119f9b7667f6368684f02455e0`. Release tag v0.2.0 at `480195f05fb2d1ed6c71dceabf4ba54b8bed69db`. Lab evidence revision `387145a00cb5f3ca645cdfac7ae63a1fa7bffd2d`. Python 3.11.9, Linux lock with verified hashes, one OpenBLAS thread per process. The run records contain exact model, inputs, mesh, fixture and frozen-asset digests.

## Observed results

| Control | v0.2.0 | M6 candidate |
|---|---:|---:|
| Four Q identities, mean held-out silhouette IoU | 62.37% | 62.37% |
| Four Q identities, mean symmetric posed residual | 36.61 mm | 36.61 mm |
| Four Q identities, mean observed UV coverage | 37.28% | 37.28% |
| Four Q identities, body and top USDZ completed | 4/4 | 4/4 |
| Independent stylized clothed adverse, complete target reconstruction | 0/4 | 0/4 |
| Single sequential synthetic raster profile, wall time | 14.92 s | 14.92 s |
| Same profile, peak RSS (decimal MB) | 261.74 | 261.14 |
| Same profile, garment stage | 1.07 s | 1.78 s |
| Same profile, USDZ package bytes | 1,150,032 | 1,145,820 |

The Q photo runs used one identical frontal input per identity with identical frozen geometry, detection model and fixed held-out cameras. Per-case quality results matched exactly. The results establish non-regression over one development source family. The runtime comparison is a single matched Linux pair, so it gives no variability bound. The local exact repair proposals for the two rejected ease-6 photo configurations took 2.61 s and 6.46 s respectively in the replay.

The separately sourced clothed control is [Cesium Man](https://github.com/KhronosGroup/glTF-Sample-Assets/blob/e124e8d8d7330a5372bc2b4d00d39a4a9d7997ea/Models/CesiumMan/LICENSE.md), Cesium (2017), CC-BY-4.0. Asset SHA-256 is `b7001eaeea8254bd44773bcd247e78696d94169388fbb2a1800fc69434e777d9`. The Blender renderer used a uniform material without the trademark texture and two frame states from the same character. Three of four cases per version had no aligned subject masks. The articulated four-view fit did not contain the frontal target alignment. Keep all eight attempted executions in the denominator. These are adverse controls. They leave realistic independent facial and anatomical coverage open. The Blender Studio realistic mesh asset bundle and its official mirror both returned HTTP 403 in this environment.

## Targeted qualification

- The mandatory editable suite ran against the same seven historical cases. Four native layered files passed direct Blender 4.5.17 USDZ import, independent body and layer material bindings, 163-bone armature motion, weight normalization, garment vertex editing, save/reopen and safe garment removal. Three failed exact collision validation before import. Candidate export readiness is 4/7.
- Calibrated numeric checks executed 33 projection indices and 66 signed rotations over 11 authored reference frame configurations. The largest coordinate error was about 0.000022 px. The largest reported global geodesic error was 0.017° against Blender float32 matrices, with point error below 0.00003 mm. These synthetic probes qualify numerical coordinate conversion. The anatomical correspondence and visibility labels remain separate gates.
- The known-effect neutral torso ratio moved 1.02590 → 1.15215 for a typed target of 1.14680. Its bounded fitting tests show the intended regional response. No independent commercial photo or deployment accuracy follows.
- The prior independent same-family direction, geometry, facial and reference results remain part of the [checkpoint evidence](M6_VALIDATION_CHECKPOINT.md). No failed candidate was promoted.

## Reproduction

Fetch the pinned release, product and Lab revisions. Use the hash-locked Python 3.11.9 environment, the original Q workspace with pinned MakeHuman and detector assets, and Blender 4.5.17 with direct USD support for export checks. The outputs are local paths. Preserve raw source meshes outside Git.

1. For the four quality cases, call `tools/benchmark_native.py` for the exact native-1 manifests identified in `paired-q-final.json` under each product checkout. Use the frontal target, the same MakeHuman asset directory and pose task, and `--garment top`. Evaluate both output roots with `tools/m6/evaluate_end_to_end.py`, fixed camera masks and 12,000 samples at seed 2473.
2. Run `tools/q/followup/layered_export.py` and `tools/m6/reexport_q_garment.py` on the historical stored projects. Replay the independent layer with `tools/q/followup/independent_layer_export.py --exact-repair`. Run `tools/q/followup/blender_roundtrip.py --strict` on the successfully exported outputs and retain rejected cases in the same denominator. Run `tools/m6/localize_garment_failure.py --ease 6` for indexed native failure regions.
3. Render the separately sourced test with `blender -b -P tools/m6/render_independent_cesium_fixture.py -- CesiumMan.glb OUTPUT`. Run the same native benchmark for both generated poses and both native-1/native-4 manifests. Record missing target alignment explicitly.
4. Run `tools/m6/calibrated_anatomy_controls.py` with the USD-capable Blender Python runtime and `tools/m6/torso_ratio_known_effect.py` with the stored canonical Q project. Run `profile_pipeline` from each product revision's `tools/verify_runtime_assets.py` in fresh temporary folders using the same frozen body.

[Reproduction inputs, raw measurements and output hashes](https://github.com/egenovese-de/Human3D-2.0/tree/387145a00cb5f3ca645cdfac7ae63a1fa7bffd2d/DOCS/m6/completion).
