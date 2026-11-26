# Q reproducibility manifest

- Release commit `480195f05fb2d1ed6c71dceabf4ba54b8bed69db`. Initial Lab `3828e922466bb53a8110114553b4aaa1c11fd758`. Latest experimental scripts source commit `7e7233c4de50d41b126cfd3c7af622239dbcef1a`.
- Read upstream asset digests from the release manifests and obtain the documented Pose Landmarker Lite v1. The Lab records the verified bytes in [manifest.json](q/manifest.json).
- MB-Lab commit `063bff04e60f3e7c651fda628c30f5d83f3f3078`. Use its local `data/humanoid_library.blend` and joint JSON files. Blender 4.3.2. Linux 6.18.57, Python 3.11.9, x86_64, NumPy 1.26.4.
- Use a CPython 3.11 virtual environment with `--require-hashes --no-deps -r <release>/requirements-linux.lock`. Supply libEGL, libGL and libGLESv2. The host retry used Debian libgles2 from its upstream package path with LD_LIBRARY_PATH pointing to a local extraction.
- Commit Lab scripts before running the unchanged historical and native runners. Set `PYTHONPATH=<release>/src:<lab>/tools` and `OPENBLAS_NUM_THREADS=1`. Set `QT_QPA_PLATFORM=offscreen` for unittest discovery in the release.
- Seed 2471 for photographic variants and 2473 for area sampling; no stochastic production settings changed. Both held-out orientations are explicit in each manifest. Use distinct empty destinations for the native benchmark and historical baselines.
- `render.py`, `depth.py`, `stress_cameras.py` and `comparison.py` run inside Blender with `-b -P script -- arguments`. For `stress_cameras.py`, add the Lab script directory to Blender's sys.path before loading. Use `--python-exit-code 1`. Other scripts provide arguments via `--help`, except `photographic.py`, `stress_photographs.py` and `validate.py` which take the pilot path positionally, and `validate.py` also takes the JSON output path.
- Recommended execution sequence: provision pinned runtime, run existing `benchmark_geometry.py --regional --carve --independent`, build metric Blender fixtures, composite opaque photographs, validate, run native one and four view manifests, run `evaluate.py` and `ablate.py`, run detector stress and components, and build the comparative raster atlas. Use `evaluate.py --metrics-only` to attach native equivalent shape measurements after the independent calibration jobs. For the supplemental view sweep run extra_views.py in Blender, then view_repeat.py. Additional geometry diagnostics are circumference.py, proportions.py and the Blender volume.py script. Run this consolidation script with scratch root and Lab directory.
- [Raw measurement summaries](q/measurements.json) retain per-view outcomes, failed preflights, directional measurements, deformation checks and instrument output. No large assets are included.

## Follow-up runtime and sequence

- Release tag `v0.2.0` resolves to `480195f05fb2d1ed6c71dceabf4ba54b8bed69db`. The follow-up begins on `c664fabe716ced28bc43d5e23f974b307234f19f`. Run the drivers from the publication commit containing this manifest and retain that commit with derived results.
- Verified CPython 3.11.9, NumPy 1.26.4, Linux 6.18.57. The lock-compatible site packages from the pilot were reused with a fresh matching interpreter. Existing Lab generated projects and earlier measurements come from the pinned pilot and holdout protocols.
- MakeHuman revision `1f508f6083b2f823dab15de924b3bde72e08d77c`. MB-Lab revision `063bff04e60f3e7c651fda628c30f5d83f3f3078`, blend SHA-256 `ae2a03430be1ef0f74a9bfa01136579e88beb521c9db7d496b5921bec6d1cd4e`. Pose model SHA-256 `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`.
- The host Blender 4.3.2 build renders calibrated views and comparison images but lacks `WM_OT_usd_import`. The official Blender LTS archive URL returned 403 and a mirror path returned 404. The Blender Foundation `bpy` wheel 4.5.17 for CPython 3.11 x86_64 has SHA-256 `967ad057646e98666f85057ee7259cbcf8c0d47f9648ab45bd72ac8453aad93a`. Install it in an isolated Blender environment and verify the registered USD import operator before processing the USDZ files.
- Put `<release>/src`, `<lab>/tools` and `<lab>/tools/q` on `PYTHONPATH`. Use the verified release lock for product dependencies, `OPENBLAS_NUM_THREADS=1`, `QT_QPA_PLATFORM=offscreen` and the verified system GLES library where required.
- Run `rig_fixtures.py` from `tools/q/followup` using the Blender Python environment and pinned MB-Lab checkout. Run `rig_benchmark.py`, then the Blender comparison renderer on generated comparison packs. Run `visibility_truth.py` before `evidence_visibility.py`. Run `clothing_fixtures.py` before `clothing_benchmark.py`, `garment_collision.py` and `reference_diagnostics.py`. Use a fresh dataset output root unless resuming the same generator revision.
- Run the direct, canonical transfer, calibrated, factorial and fit-acceptance drivers on separate output paths. The `pose_camera.py --truth-mask` mode produces the partial joint-ablation records. Run the texture fixture in the USD-enabled Blender Python environment. Use `layered_export.py` to build separate release USDZ inputs and `blender_roundtrip.py` to inspect and save them locally. Drivers expose positional arguments through `--help`.
- Run `python -m unittest discover -s <release>/tests`. Compare per-case metrics with the published JSON and allow elapsed-time variability across executions.
- The independent ring-mesh export runs through `independent_layer_export.py` and the same USDZ round-trip runner. `blender_layers_atlas.py` renders the directly imported assets and a controlled armature edit. Blender Foundation publishes the [4.5 LTS release](https://www.blender.org/releases/4-5/) and the [module distribution](https://pypi.org/project/bpy/4.5.17/).
- Twelve unchanged articulated cases produced identical numeric outputs in a repeated execution. Two asymmetric fixture inputs were intentionally revised and excluded from that equality check. Reproducibility artifacts record the final input hashes and the repeat comparison.
- Run `face_capacity.py` on the compatible expanded human presets. `face_variations.py` regenerates separate profile/expression geometry from the expression target sources and reports their input hashes.

## Finalization reproduction

The finalization starts at Lab parent `9cc1552b201d55e97eacbb1959b009e139ae85d8`. Use the unchanged release commit `480195f05fb2d1ed6c71dceabf4ba54b8bed69db` and the pinned inputs described above. Configure two Python 3.11 environments, one for the release lock and one with Blender's bpy 4.5.17 plus the pinned numeric and release packages. Place release `src` and `tools`, and Lab `tools`, `tools/q` and `tools/q/followup` on PYTHONPATH, with release `src` first. The finalization jobs reuse the existing verified lab datasets and native project fixtures. They require no additional external photo or asset download.

Set `LAB` to the Lab checkout, `PREVIOUS` to the pilot/holdout output root with `assets`, `holdout`, `holdout-native`, `holdout-mixed` and `eval`, and `FOLLOWUP` to the prior extension root with `rig-fixtures`, `clothes` and `visibility.json`. Create a fresh `OUT` directory with `mkdir -p "$OUT"`. Commands below assume `python` from the release virtual environment and `$BLENDER_PY` from the Blender virtual environment.

```bash
f="$LAB/tools/q/followup"
q="$LAB/tools/q/finalization"
python "$f/fit_acceptance.py" "$PREVIOUS" "$OUT/acceptance.json"
python "$q/fit_screen.py" "$PREVIOUS" "$OUT/acceptance.json" "$OUT/fit-projects" "$OUT/fit-screen.json"
python "$q/rig_landmarks.py" "$FOLLOWUP/rig-fixtures" "$PREVIOUS" "$OUT/landmark-photos" "$OUT/rig-landmarks.json"
"$BLENDER_PY" "$q/face_anchors.py" "$FOLLOWUP/rig-fixtures" "$PREVIOUS/assets/pose.task" "$OUT/landmark-photos" "$OUT/face-anchors.json"
python "$q/annotation_plate.py" "$FOLLOWUP/rig-fixtures" "$OUT" "$OUT/annotation-plate.png"
python "$q/evidence_boundaries.py" "$OUT/evidence-boundaries.json"
python "$q/appearance_visibility.py" "$PREVIOUS" "$OUT/appearance-visibility.json"
python "$f/evidence_visibility.py" "$FOLLOWUP/rig-fixtures" "$PREVIOUS" "$FOLLOWUP/visibility.json" "$OUT/evidence-photos" "$OUT/evidence.json"
python "$f/pose_camera.py" "$PREVIOUS" "$OUT/factorial.json"
python "$f/pose_camera.py" "$PREVIOUS" "$OUT/upstream.json" --truth-mask
python "$f/geometry_transfer.py" "$PREVIOUS" "$OUT/transfer-with-native.json" --include-native-fit
python "$f/reference_diagnostics.py" "$PREVIOUS" "$FOLLOWUP/clothes" "$OUT/reference-photos" "$OUT/references.json"
python "$LAB/tools/q/mixed_references.py" score "$PREVIOUS/holdout" "$PREVIOUS/holdout-native" "$PREVIOUS/holdout-mixed" "$OUT/mixed-score.json"
for identity in f_af01 m_la01; do
  for treatment in different-pose contradictory; do
    python "$q/reference_sets.py" "$PREVIOUS" "$OUT/reference-projects" \
      "$OUT/reference-$identity-$treatment.json" "$identity" "$treatment"
  done
done
python - "$OUT" <<'PYTHON'
import json
from pathlib import Path
import sys
out = Path(sys.argv[1])
rows = [row for identity in ("f_af01", "m_la01") for treatment in ("different-pose", "contradictory")
        for row in json.loads((out / f"reference-{identity}-{treatment}.json").read_text())]
(out / "reference-sets.json").write_text(json.dumps(rows, indent=2) + "\n")
PYTHON
python "$q/input_inventory.py" "$PREVIOUS" "$FOLLOWUP" "$LAB/DOCS/q/followup/fixture-index.json" "$OUT/input-hashes.json"
"$BLENDER_PY" "$f/garment_collision.py" "$FOLLOWUP/rig-fixtures" "$FOLLOWUP/clothes" "$PREVIOUS" "$OUT/garment.json"
"$BLENDER_PY" "$q/garment_pose.py" "$PREVIOUS" "$OUT/garment-pose.json"
python "$q/summarize.py" "$OUT" "$OUT/summary.json"
```

Refer to [fixture index](q/followup/fixture-index.json) and [dataset manifest](Q_DATASET_MANIFEST.md) for generation and input identity. Finalization input hashes appear in the [reused input inventory](q/finalization/input-hashes.json). The finalization retained all tested identities and treatments for the published fit screen. Compare measurements by fixture and condition, ignoring runtime and using numerical precision appropriate to the installed platform. The [artifact hashes](q/finalization/SHA256SUMS) verify the exact published bytes.
