# Human3D stabilization candidate installation

## Install on Windows

Use a Windows x64 machine, Git and CPython 3.11.9. From an empty working directory, clone the repository and check out the v0.2.0 tag once published. Historical candidate evidence is in the [candidate record](STABILIZATION_CANDIDATE.md).

```powershell
git clone https://github.com/egenovese-de/Human3D-2.0.git
Set-Location Human3D-2.0
git checkout --detach v0.2.0
py -3.11 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --only-binary=:all: --require-hashes --no-deps -r requirements-windows.lock
& $python tools/build_verified_wheel.py dist
$wheel = Get-ChildItem dist -Filter human3d-*.whl
& $python -m pip install --no-deps $wheel.FullName
& $python -m pip check
.\.venv\Scripts\human3d.exe --version
.\.venv\Scripts\human3d-desktop.exe
```

Use a fresh checkout or empty `dist` directory so the install selects the wheel just built. The builder uses a clean Git snapshot twice, compares the SHA-256 hashes and reports the source revision. Git, PyPI and separately provisioned runtime assets require access during setup. The wheel contains application code and the application license. Dependencies and upstream assets are provisioned separately.

On Ubuntu 24.04 install `libegl1 libgl1 libgles2 libglib2.0-0t64`, use `requirements-linux.lock`, and run the same builder and pip commands via `.venv/bin/python`. Launch `.venv/bin/human3d-desktop` in a desktop session.

## Configure and run reconstruction

1. Place `base.obj`, `default.mhskel`, `default_weights.mhw` and the 14 supported `.target` files in one local directory. Use the revision, paths and digests in the [mesh and rig manifest](manifests/makehuman-v1.3.0.json) and [morph manifest](manifests/makehuman-morph02.json). The [asset preflight notes](S1-003_ASSET_PREFLIGHT.md) describe verification.
2. Download the pinned [Pose Landmarker Lite v1 model](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task) to a local directory. Expected SHA-256 is `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`.
3. In the desktop application choose **New project**, **Add photos** and **Freeze rest body**. Select a target in the thumbnails. Use **Review target mask**, select the model and apply a reviewed mask. **Fit included photos** builds one shared body from included views. Select **Export USD**, **Inspect appearance** or **Assemble garments** for the desired output.
4. To verify a real Windows 11 client install, run the strict probe from the checkout in a fresh environment. Preserve its output and the Git SHA.

```powershell
& $python tools/verify_windows_install.py --require-windows11 --wheel $wheel.FullName --report windows11-install.json
```

## Troubleshooting

| Symptom | Action |
|---|---|
| pip reports a Python or wheel incompatibility | Verify CPython 3.11.9 x64 and the platform lock. Start again in an empty virtual environment. |
| A bootstrap asset or model fails digest validation | Retrieve the pinned bytes from the documented source and verify the filename and SHA-256. |
| The detector subprocess fails on Ubuntu | Verify that EGL, GL and GLES are present and the pinned dependencies pass `pip check`. Retry detection after installing missing system libraries. |
| The application cannot find a subject or reports incomplete evidence | Use an unobstructed full-body view, confirm the target and review the mask. |
| Appearance or garment actions are disabled | Apply a reviewed mask for the target and run **Fit included photos**. Include only useful photos of the same subject. |
| OpenUSD opens without expected textures | Use the textured `.usdz` export and move the intact package. For Blender, use an importer with USD, material and skeleton support. |

For an offscreen GUI smoke test with authorized synthetic photos, run `tools/verify_candidate_gui.py --assets <directory> --model <file> <target> <reference>` against the installed wheel with `QT_QPA_PLATFORM=offscreen`. The test builds a temporary project and verifies its exports.
