# Reproduce G4

Use the G4 Lab branch, detached M6 `e0ae4eae57347466b5757bbcdaaa7194bdd31c94`, and upstream MakeHuman `1f508f6083b2f823dab15de924b3bde72e08d77c`. The G4 Actions job uses the permanent Lab Runtime and regenerates its MakeHuman input. The full local benchmark reuses admitted exports:

- G2 evidence SHA-256 `dbe8cc5d8535d40e572c63f83dc2292bbc8700f3ebb3af7b015bb34b43d69355`
- G3 evidence SHA-256 `f6b9e892dbc2421d17d889ece3af75c4064989d3e373109918ae51d89ae9148c`

Use G2 paths `geometry/A_*.npz`, `evidence_maps/A_*`, and `measurements/config.json`. Use G3 paths `measurements/orientation.json` and `articulated/A_*`. Set U to upstream MakeHuman code, PRODUCT to M6, PY and BLENDER to the Lab executables, POSE to the pinned pose model, G2 and G3 to the extracted bundles.

```bash
export U OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONPATH="$PRODUCT/src:$PWD/tools/g1:$PWD/tools/g2:$PWD/tools/g3:$PWD/tools/g4:$U:$U/lib:$U/apps:$U/core:$U/shared"
mkdir -p out
g++ -O3 -shared -fPIC tools/g2/raster.cpp -o out/raster.so
"$PY" -m unittest discover -s tools/g4 -v
"$PY" tools/g4/benchmark.py --g2 "$G2" --g3 "$G3" --raster out/raster.so --output out/A_main
"$PY" tools/g4/registration_ablation.py "$G2" "$G3" out/raster.so out/registration_ablation
"$PY" tools/g4/articulated_controls.py "$G2" "$G3" out/raster.so "$POSE" out/articulated
"$BLENDER" -b -t 2 --factory-startup --python-exit-code 1 --python tools/g2/surface.py -- out/surface.json out/A_main/A_*/*.npz
"$BLENDER" -b -t 2 --factory-startup --python-exit-code 1 --python tools/g4/blender_g4.py -- out/A_main/A_muscular/A_muscular.npz "$U/data/3dobjs/base.obj" out/render
```

The four local MB-Lab subjects can be regenerated from the same restricted historical input set via G1 and G2's independent admission commands. Render them with the G2 Workbench fixture script, use `independent_rgb.py` to build the masks and run `benchmark.py` with `--references` and `--config`. Release only numeric B measurements.

For the standalone fitter run `registered_fit.py MANIFEST BASIS RASTER.so OUTPUT`. The manifest schema is 1 with a `views` list. Each view has a unique `key`, complete G2 `camera` object, `camera_source`, `scale_source`, optional G3 `pose` in radians and registration uncertainty, plus a relative path to an NPZ containing `mask`, `states`, `confidence`, and optional `outer_only`. The result contains canonical points, topology, parameters and disposition. The CLI does not create an animation rig, does not register raw photographs, and does not consume target metadata at this stage.
