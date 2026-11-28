# Reproduce G6

Use the G6 branch, G4 commit `ca90165d259bada9b3cea945d1227be0f83656ef` and MakeHuman `1f508f6083b2f823dab15de924b3bde72e08d77c`. Follow the M7 Linux hash lock and G5 prerequisites for the product, MediaPipe shared libraries, historical authorized MB-Lab meshes and the verified G5 evidence ZIP. No depth or normal model inference is needed. Use Blender 4.3.2 for numerical evaluation and the USD-enabled Blender 4.5.16 runtime for round trips.

```bash
export PYTHONPATH="$G6/src:$G6/tools/g5:$G6/tools/g6:$G4/tools/g1:$G4/tools/g2:$G4/tools/g3:$G4/tools/g4:$U:$U/lib:$U/apps:$U/core:$U/shared"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$G6"
mkdir -p out/qual out/qual_photo
g++ -O3 -shared -fPIC "$G4/tools/g2/raster.cpp" -o out/raster.so
"$PY" tools/g5/fixtures.py "$G4" "$HISTORICAL" out/refs
unzip -oq "$G5_EVIDENCE" 'rgb/A_*/*.png' -d out
for ref in out/refs/B_*.npz; do
  case_name=$(basename "$ref" .npz)
  blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g5/render.py -- "$G4" out/refs out/rgb --case "$case_name"
done
"$PY" -m unittest discover -s tools/g6 -p test_geometry.py -v
"$PY" tools/g5/run_baseline.py "$RUNTIME" out/rgb out/baseline
for ref in out/refs/*.npz; do
  case_name=$(basename "$ref" .npz)
  "$PY" tools/g6/run.py "$RUNTIME" "$ref" "out/baseline/$case_name/calibrated" out/study
done
blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g6/qualify.py -- "$G4" out/study out/study-surface.json
for case_name in A_heldout_1 B_female_expanded B_male; do
  "$PY" tools/g6/photo.py "$RUNTIME" "out/refs/$case_name.npz" out/baseline out/raster.so out/rgb out/photo
  "$PY" tools/g6/oracle_transfer.py "out/study/$case_name" out/baseline out/raster.so out/oracle
done
for lane in photo oracle; do
  blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g6/qualify.py -- "$G4" "out/$lane" "out/$lane-surface.json"
done
"$PY" tools/g6/pose.py out/study out/baseline out/pose.json
"$PY" tools/g6/posture.py "$G4/DOCS/g2/G2_DATASET_MANIFEST.json" "$HISTORICAL" out/baseline out/study out/posture
blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g6/qualify.py -- "$G4" out/posture out/posture-surface.json
blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g6/audit_structure.py -- out/study out/poses.npz out/structure.json
"$PY" tools/g6/sections.py out/study out/baseline out/sections.json
blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g6/resolution.py -- out/study/A_slim/accepted.npz out/resolution.json
"$PY" tools/g6/diagnostics.py out out/raster.so
"$PY" tools/g6/report.py out "$G5_EVIDENCE" DOCS/g6
```

For A_slim and B_male run `tools/g6/export.py out/study/CASE out/baseline out/export/CASE` and pass the D0 and R2 fine USDs through `tools/qualify_m7_blender.py` inside USD-enabled Blender. Rerun the report after round-trip JSON is present. Store B mesh and USD outputs locally under the authorized dataset controls. Use `tools/g6/visual.py` for matched-view comparisons, vertex color and the editable scene. The submitted visual comparisons use the same perspective cameras across alternatives. `tools/g6/atlases.py` composes actual Blender renders and numerical section geometry.

Run the sampled volumetric guard after the geometry study with `tools/g6/volume_guard.py out/study out/baseline out/volume`. Re-evaluate the directory with `qualify.py -- G4 out/volume out/volume-surface.json`. This fits one smooth field from the M7 anchor to the previously retained fine-FFD result and screens determinant samples independently of the surface guards.
