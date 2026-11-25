# Human3D 2.0

The M1 desktop build is on `development/m1`. It supports a single-target
reconstruction flow with mask review, initial alignment, bounded body fitting,
neutral and posed inspection, and rigged OpenUSD export.

## Run the M1 desktop build

Use CPython 3.11.9 and the lock file for your platform. On Windows run the
following from the repository root.

```powershell
python -m pip install --require-hashes --no-deps -r requirements-windows.lock
python -m pip install --no-deps .
human3d-desktop
```

On Linux use `requirements-linux.lock` and the system libraries in [RUNTIME](DOCS/RUNTIME.md).

1. Create a project and import a full-body target photograph.
2. Choose **Freeze rest body** and select the directory with the verified
   MakeHuman assets. Place `base.obj`, `default.mhskel`, `default_weights.mhw`
   and the eight `.target` files from the [MORPH-02 manifest](DOCS/manifests/makehuman-morph02.json)
   in that directory. The [MakeHuman manifest](DOCS/manifests/makehuman-v1.3.0.json)
   identifies the pinned upstream revision and exact asset paths. The app
   checks the expected hashes.
3. Select **Review target mask**, then choose the local
   [Pose Landmarker Lite v1 bundle](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task).
   Review the foreground and adjust the alignment if needed.
4. Select **Approve alignment and fit**, then close the review dialog.
   Use **Inspect fitted body** or **Export USD**. Fit and correction state
   live in the current session.

The initial pose uses image-plane limb directions. The first local empirical
test is tracked in the [test plan](DOCS/EMPIRICAL_TEST_PLAN.md).

## Product vision

Human3D reconstructs editable, reusable 3D human assets from one or more photographs of the same person. A selected target determines pose and appearance; other views inform shared neutral anatomy. Planned outputs include independent clothing geometry, UVs, materials, skeleton, skin weights and editable OpenUSD for Blender.

## Documentation

- [ARCHITECTURE](DOCS/ARCHITECTURE.md)
- [BACKLOG](DOCS/BACKLOG.md)
- [TRACEABILITY](DOCS/TRACEABILITY.md)
- [DEPENDENCIES](DOCS/DEPENDENCIES.md)
- [TEST_CI_STRATEGY](DOCS/TEST_CI_STRATEGY.md)
- [MILESTONE_ACCEPTANCE](DOCS/MILESTONE_ACCEPTANCE.md)
- [EMPIRICAL_TEST_PLAN](DOCS/EMPIRICAL_TEST_PLAN.md)
- [DECISIONS](DOCS/DECISIONS.md)
