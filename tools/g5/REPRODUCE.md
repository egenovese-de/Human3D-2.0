# Reproduce G5 on Linux CPU

Use qualified M7 at `020fcc793e7417d6927d9e07346678e110ae9ddc`, G4 at `ca90165d259bada9b3cea945d1227be0f83656ef`, and MakeHuman at `1f508f6083b2f823dab15de924b3bde72e08d77c`. The G5 branch is based on qualified M7 and contains no application source edits. Use the original authorized MB-Lab mesh directories from G4 for Family B. Their bytes are verified against the G2 manifest. Maintain the G4 distribution restrictions.

Use Python 3.11.9, Blender 4.3.2, a C++ compiler, and the M7 Linux hash lock. Install ONNX Runtime 1.24.1 for depth. For DSINE, provision PyTorch 2.7.1+cpu and geffnet 1.0.2 without allowing the resolver to substitute a CUDA-enabled PyTorch package. Obtain pinned checkpoints and media according to the asset and model manifests. Ensure the MediaPipe C shared library can resolve the system GLESv2 and EGL libraries.

Set `G5` to this checkout, `G4` to the pinned G4 worktree, `U` to the upstream MakeHuman code directory, `RUNTIME` to the preflight-verified M7 runtime, `HISTORICAL` to the authorized MB-Lab directories, and `MODELS` to local predictor assets. In the examples below, `DSINE` points to the pinned DSINE source and `PY` is the Python executable.

```bash
export U OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH="$G5/src:$G5/tools/g5:$G4/tools/g1:$G4/tools/g2:$G4/tools/g3:$G4/tools/g4:$U:$U/lib:$U/apps:$U/core:$U/shared"
cd "$G5"
mkdir -p out
g++ -O3 -shared -fPIC "$G4/tools/g2/raster.cpp" -o out/raster.so
"$PY" tools/g5/fixtures.py "$G4" "$HISTORICAL" out/refs
blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g5/render.py -- "$G4" out/refs out/rgb
"$PY" tools/g5/predict.py depth "$MODELS/depth.onnx" out/rgb out/pred
"$PY" tools/g5/predict.py normal "$MODELS/dsine.pt" out/rgb out/pred --source "$DSINE"
"$PY" tools/g5/quality.py out/refs out/rgb out/pred out/raster.so out/maps
blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g5/verify_rays.py -- "$G4" out/refs/A_high_mass.npz out/maps/A_high_mass out/rays.json
"$PY" tools/g5/run_baseline.py "$RUNTIME" out/rgb out/baseline
"$PY" -m unittest discover -s tools/g5 -p test_evidence.py -v
for file in out/refs/*.npz; do
  case=$(basename "$file" .npz)
  "$PY" tools/g5/benchmark.py "$RUNTIME" "out/rgb/$case" "$file" "out/pred/$case" out/raster.so "out/baseline/$case/calibrated" "out/calibrated/$case"
done
blender -b -t 2 --factory-startup --python-exit-code 1 --python tools/g5/measure.py -- "$G4" out/calibrated out/calibrated-surface.json
```

Use `--estimated` with the matching estimated baseline directory for admitted automatic registrations. Use `--views 1|2|4|8` with a distinct output directory for each branch of the nested-view benchmark. Use `--perturb=yaw:8` and separate output directories for the registered-camera stress matrix. `stress.py` takes the M7 runtime, the A high-mass reference NPZ, raster shared library, calibrated baseline directory and stress output. Measure its outputs using `measure.py --stress`.

The predictor runs are sequential to keep initialization and peak RSS separate. Run fitting sequentially or in small batches and preserve individual case logs. Concurrent task wall times are workload measurements. Use a dedicated single-case repeat for isolated latency.
