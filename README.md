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

## Run the M2 desktop build

Check out `development/m2` and use the same installation and verified local
assets as M1. For the additional torso controls, add the six bust, shoulder
and waist measurement targets listed in the pinned MakeHuman manifest and
freeze the rest body again.

Import reference photographs of one subject. Use a photo's context menu
to include, exclude or retry detection. Select **Fit included photos** to
calculate a shared body and report regional coverage and overlap by photo.
Changing the target selects a different view of the same shared revision.
**Inspect fitted body** compares bootstrap, fitted neutral and posed geometry.
Use **Edit body control** and **Restore body revision** to manage revisions for
the current reference set. **Export USD** writes the current target pose.

## Run the M3 desktop build

Check out `development/m3` and use the M2 installation and local assets.
Run **Fit included photos** again for projects fitted by earlier builds.
**Inspect fitted body** shows the target articulation and allows bounded
per-limb corrections. Pose corrections apply to the active session and are
included in export. The relative foot-height check does not estimate a floor.

**Inspect appearance** shows the UV atlas, observed coverage, padding, and
skin-color candidates from local image evidence. The texture prioritizes the
target and balances exposure across visible reference samples. Unseen areas use
neutral color where nearby padding is unavailable. Use **Export textured USDZ**
to package the mesh, rig, pose, material and albedo together.

## Run the M4 desktop build

Check out `development/m4` and use the same desktop setup and local assets.
Sync to the updated platform lock. On Linux the detector also needs `libgles2`.
Fit the target or included photos, then choose **Assemble garments**. Fit a
close-fitting top, shorts or trousers and inspect the photo coverage. Use
**Apply edits** for ease and hem changes. Open the posed 3D preview or remove
a garment from the assembly. A base top may be paired with an outer top if
the sampled layer separation passes.

**Export garment assembly** packages the body and separate rigged garment
meshes with materials, textures and a sampled clearance manifest. Exports
are blocked when sampled penetrations exceed tolerance. The assembly draft
is local to the dialog. Save an export to keep the resulting meshes.

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
