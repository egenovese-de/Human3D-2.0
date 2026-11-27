# Reproduce G2

Use the isolated G2 branch, the untouched M6 source at e0ae4eae57347466b5757bbcdaaa7194bdd31c94, and MakeHuman v1.3.0 at 1f508f6083b2f823dab15de924b3bde72e08d77c. The G2 Actions workflow provisions and verifies the permanent Lab Runtime. Local measurements used Python 3.11.9 with the Lab packages and the host Blender 4.3.2.

Set PY to the Lab Python executable, BLENDER to the Blender executable and POSE to the manifest-verified pose_landmarker_lite.task. Set U to the upstream makehuman code directory and PRODUCT to the checked-out M6 source.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 QT_QPA_PLATFORM=offscreen
export PYTHONPATH="$PRODUCT/src:$PWD/tools/g1:$PWD/tools/g2:$U:$U/lib:$U/apps:$U/core:$U/shared"
mkdir -p g2-out
g++ -O3 -shared -fPIC tools/g2/raster.cpp -o g2-out/raster.so
"$PY" tools/g1/g1_benchmark.py --output g2-out/references
"$PY" tools/g2/references.py g2-out/references
for f in g2-out/references/[AB]_*.npz; do
  "$BLENDER" -b -t 2 --factory-startup --python-exit-code 1 --python tools/g2/blender_evidence.py -- fixtures "$f" "g2-out/rgb/$(basename "$f" .npz)"
done
"$PY" tools/g2/photographic.py --references g2-out/references --rgb g2-out/rgb --output g2-out/experiment --model "$POSE" --raster g2-out/raster.so
"$PY" tools/g2/product_baseline.py g2-out/rgb g2-out/references "$POSE" g2-out/experiment/product
"$PY" tools/g2/geometric_controls.py g2-out/references g2-out/experiment/controls g2-out/raster.so g2-out/experiment/measurements/config.json
"$PY" tools/g2/conditions.py g2-out/references/A_high_mass.npz g2-out/experiment/measurements/config.json g2-out/experiment/conditions g2-out/raster.so
"$PY" tools/g2/stereo.py g2-out/references/A_high_mass.npz g2-out/experiment/stereo g2-out/raster.so
"$PY" tools/g2/correspondence.py g2-out/references g2-out/experiment/measurements/config.json g2-out/experiment/correspondence g2-out/raster.so
"$PY" tools/g2/landmark_regions.py g2-out/experiment "$POSE" g2-out/experiment/measurements/landmark-regions.json
"$BLENDER" -b -t 2 --factory-startup --python-exit-code 1 --python tools/g2/surface.py -- g2-out/experiment/measurements/surface.json g2-out/experiment/meshes/*.npz
```

For Family B, add `--independent /authorized/holdout` to the G1 benchmark invocation. Keep the G1 MB-Lab fixture manifests and exact local mesh inputs. The dataset manifest identifies the two SHA-256 values; restricted geometry, rendered source photos and reconstructible maps stay local.

The optional depth command requires ONNX Runtime 1.24.1 and the separately obtained 98.8 MB Depth Anything V2 Small ONNX file pinned in `depth_probe.py`. Run `"$PY" tools/g2/depth_probe.py g2-out/experiment g2-out/references "$DEPTH_WEIGHTS" g2-out/raster.so`. The runtime module is loaded locally and does not contact an inference service.

Use `surface.py` on each control set separately to retain separate per-subject files and `blender_evidence.py -- compare` on a combined MakeHuman mesh file with a `best` key for the selected result. Rendered comparative views and editable assets shipped in the evidence archive are generated results.

Additional isolated operations:

```bash
"$PY" tools/g2/independent.py /authorized/holdout g2-out/references
"$PY" tools/g2/direct_oracle.py g2-out/references g2-out/experiment/measurements/config.json g2-out/experiment/direct
"$PY" tools/g2/matched_ablations.py g2-out/experiment g2-out/experiment/ablations g2-out/raster.so
"$PY" tools/g2/comparison_pack.py g2-out/experiment g2-out/A_high_mass.npz A_high_mass rgb_gap
"$BLENDER" -b -t 2 --factory-startup --python-exit-code 1 --python tools/g2/blender_evidence.py -- compare g2-out/A_high_mass.npz g2-out/renders/A_high_mass
```

Run the expanded admission before rendering the reference loop if both additional historical specimens are available. Run `surface.py` separately on candidate mesh sets from product, depth, ablation, controls and direct geometry; keep their output JSON names unique. No source scan or model weights are in the evidence archive.
