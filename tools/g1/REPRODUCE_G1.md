# Reproduce G1

Use checked-out Human3D product `e0ae4eae57347466b5757bbcdaaa7194bdd31c94`, Lab base `66d84ba5775b0ab22f6e587e83efa0999180255c`, and MakeHuman `1f508f6083b2f823dab15de924b3bde72e08d77c` (v1.3.0). Use Python 3.11.9 and the permanent Lab runtime hashed dependency lock. Install the same Linux operating-system libraries as the workflow on Linux. Blender must be headless with USD support for the export round-trip. Local G1 used 4.5.17 with USD, while the Lab CI uses manifest-pinned 4.5.3.

The core benchmark sets `U` to the MakeHuman code directory (the upstream checkout's `makehuman` folder). Add Human3D's `src` and `$U:$U/lib:$U/apps:$U/core:$U/shared` to `PYTHONPATH`. Set `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. Run:

```bash
python g1_benchmark.py --output g1-run
python g1_observability.py --configs g1-run/configurations.json --output g1-run/observability.json
python g1_dependencies.py g1-run
python g1_basis_ablation.py g1-run
python g1_exports.py g1-run
for file in g1-run/A_*.npz; do
  blender -b --factory-startup --python-exit-code 1 --python g1_render.py -- "$file" g1-renders
done
blender -b --factory-startup --python-exit-code 1 --python g1_blender_roundtrip.py -- g1-run/export
```

Use `g1_exact_surface.py` from a Blender-capable Python runtime with matching benchmark dependencies, passing `g1-run` as the first argument. The local run uses the Blender 4.5.17 bpy wheel in a Python 3.11 environment and the same scientific runtime on its module path. Reference hashes and parameter seeds are in the numeric evidence.

For the independent runs add `--independent /authorized/q/holdout`. Supply the prior Q female `f_ca01` and male `m_la01` bend-0 mesh plus corresponding manifests, which the benchmark checks against their hashes. Execute `g1_independent_stance.py g1-run /authorized/q/holdout` with the Blender Python runtime. The two raw MB-Lab datasets and their editable scenes remain in authorized local storage. Public CI publishes only the permitted MakeHuman-family artifacts. The expanded probe and budget ablation use repeated sampled-point metrics and different seeds from the primary BVH score.

The result bundle includes SHA-256 sums. Reproduce the full assets check from the upstream checkout at the exact revision, using `verified_assets.json` and the three Lab manifests. The numerical Lab Runtime smoke records the actual local invocation. The headless harness loads upstream modules from the supplied checkout. No upstream program source is bundled.
