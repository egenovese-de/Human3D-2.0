# Install Human3D Empirical Desktop v1

Use Windows 11 with 64-bit Python 3.11.9 including the Python launcher. Setup needs internet access to PyPI, GitHub and the MediaPipe asset host. After setup the application can run offline on the CPU.

## Existing repository

Run these PowerShell commands. A linked working tree lets you keep your current changes in place.

```powershell
Set-Location 'C:\Users\Asus\Documents\GitHub\Human3D-2.0'
git fetch origin development/m7
git worktree add --detach '..\Human3D-M7' origin/development/m7
Set-Location '..\Human3D-M7'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Setup-Human3D.ps1
.\Launch-Human3D.cmd
```

Choose a new sibling folder name if `Human3D-M7` already exists. For a revision-stamped ZIP, extract it to a writable folder and run the last two commands there. Setup verifies the Python runtime, sets up the isolated environment, installs the hash-locked wheels, downloads and verifies assets, and launches a Qt startup smoke test. Later, double-click `Launch-Human3D.cmd`.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Runtime verification fails | Install the exact Python 3.11.9 x64 runtime with the Python Launcher and rerun setup in the M7 folder. |
| Download, wheel or asset verification fails | Consult `local-data\m7-setup.log`, restore access to the named host and rerun setup. |
| MediaPipe initialization reports a missing native DLL | Install the Microsoft Visual C++ x64 redistributable and rerun setup. |
| The window closes at launch | Read `local-data\m7-launch.log` and confirm the startup screenshot exists. |
| Engine B reports no admissible registration | Add a clear frontal full-body view or select Engine A and regenerate. |
| Target pose unavailable | Inspect or export the canonical body and try a target with visible torso and joints. |

Physical workstation qualification requires the Project Lead to run setup, generate with one and several locally authorized real photos, cancel and retry, reopen the project, and import the posed export into Blender. Capture stage timings and any errors through Export Evidence.
