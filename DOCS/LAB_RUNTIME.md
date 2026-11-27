# Permanent Lab Runtime
Windows 2022 x64 is the mandatory qualified CI platform; Linux remains supported by the lock and earlier evidence but is deferred for final qualification.
Python 3.11.9 and Blender 4.5.3 are provisioned from pinned dependencies and verified archives; do not commit binaries or runtime caches.

## Execute
On Windows with Python 3.11.9, from the lab repository root:
```powershell
git worktree add --detach .lab-source 480195f05fb2d1ed6c71dceabf4ba54b8bed69db
python tools/lab_runtime/bootstrap.py --group morph02 --group anatomical_torso
python tools/lab_runtime/verify.py --source .lab-source --source-revision 480195f05fb2d1ed6c71dceabf4ba54b8bed69db --group morph02 --group anatomical_torso
python tools/lab_runtime/runner.py --config lab/experiments/lr-009-native.json --source .lab-source --output lab-output/experiment
python tools/lab_runtime/evidence_control.py lab-output/experiment
python tools/lab_runtime/negative_control.py
```
Use a fresh output directory. For CI, update the versioned request ID in lab/experiments/request.json on lab/render; request.py validates the admitted configuration and source. Inspect Actions jobs, logs and artifact manifest. Artifacts expire after seven days; preserve approved numerical evidence in Git. No personal images, model weights or restricted historical assets in shared artifacts. See LAB_RUNTIME_LICENSES.md.
