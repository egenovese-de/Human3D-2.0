# Reproduce G3

The G3 workflow provisions the permanent Lab Runtime and runs the high-mass front and near articulated controls. Local extended runs use the G2 archive with SHA-256 `dbe8cc5d8535d40e572c63f83dc2292bbc8700f3ebb3af7b015bb34b43d69355`. Extract only `geometry/A_*.npz` and `evidence_maps/A_*/*/{rgb.png,camera.json}` to an input directory. Use M6 at `e0ae4eae57347466b5757bbcdaaa7194bdd31c94`, MakeHuman at `1f508f6083b2f823dab15de924b3bde72e08d77c`, and the same verified MediaPipe pose model as G2. The historical G2 and G3 study data contain generated MakeHuman geometry.

Set U to the upstream MakeHuman source directory, PRODUCT to the detached M6 worktree, POSE to the Lab pose model, PY to the Lab interpreter, and G2 to the extracted G2 input. Blender must support headless Workbench.

```bash
export U
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 QT_QPA_PLATFORM=offscreen
export PYTHONPATH="$PRODUCT/src:$PWD/tools/g1:$PWD/tools/g2:$PWD/tools/g3:$U:$U/lib:$U/apps:$U/core:$U/shared"
mkdir -p out/A_extended out/articulated out/comparison publish
g++ -O3 -shared -fPIC tools/g2/raster.cpp -o out/raster.so
"$PY" -m unittest discover -s tools/g3 -v
"$PY" tools/g3/benchmark.py --g2 "$G2" --model "$POSE" --raster out/raster.so --output out/A_extended
"$PY" tools/g3/orientation.py "$G2" out/orientation "$POSE" out/raster.so
"$PY" tools/g3/articulated_rgb.py out out/articulated "$POSE" out/raster.so --blender "$BLENDER"
"$BLENDER" -b -t 2 --factory-startup --python-exit-code 1 --python tools/g3/blender_g3.py -- comparison out/articulated/A_high_mass/near_articulated out/comparison
"$PY" tools/g3/visual.py out/articulated/A_high_mass/near_articulated publish/G3_Registration_Comparison.png
"$PY" tools/g3/report.py out DOCS/g3
```

Report records classify results by raw RGB, calibrated joint observations, limited capture-sector metadata and known geometry. The exact external sector and synthetic camera calibration serve as independent controls. The mesh in a G3 Blender scene represents the specific observation pose. The immutable anatomical reference is stored separately. Do not interpret the scene as an animation-ready rigged export.
