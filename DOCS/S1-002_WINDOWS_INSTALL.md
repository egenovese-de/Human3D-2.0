# S1-002 — Clean Windows installation
Status: BLOCKED; hosted Windows clean installation PASS; Windows 11 client acceptance NOT_RUN.
The hosted windows-2022 runner is Windows Server, not Windows 11. Prior run 45783389414 passed 37 tests on Windows and Linux, but is not client acceptance.
New probe tools/verify_windows_install.py (652b185b22cf83c59e59823ff9392eac58926b1e) and CI integration (549e869694a6c6e6c0b1aaed74263b04091fe854) exercise a fresh venv, binary hash-pinned dependencies, installed application, pip check, CLI, isolated native smoke (NumPy/SciPy, Pillow, MediaPipe API import, Qt window, OpenUSD file roundtrip) and regression suite. Native model inference and interactive desktop acceptance are outside this probe.
On Windows 11 x64, from a checkout of the stabilization revision, with CPython 3.11 x64 and internet access:
```powershell
py -3.11 tools/verify_windows_install.py --require-windows11 --report windows11-install.json
```
The strict flag checks registry InstallationType Client and build >=22000, rejecting Server. Retain console output, report and git revision. No photos needed. The probe uses temporary environment and synthetic files; does not install into system Python. Build isolation may download setuptools. Qt offscreen is not an interactive desktop test. Do not mark DONE until actual Windows 11 evidence is obtained. No S1-003 work.

## Verified CI results
Run 45785023597 at d7212e23693ca6674085e0d52c89e68ec013ee38: all five jobs successful. Ubuntu job 139789577027: 37 tests in 6.315s, OK. Windows job 139789577290: 37 tests in 7.196s, OK; isolated fresh venv probe step 13 successful, native runtime smoke PASS, installed regression suite 37 tests in 4.205s, OK. Report status PASS, InstallationType Server, build 20348, windows11_client false. No test correction needed. 111 test executions across three environments. Windows 11 client evidence remains unavailable; do not substitute Server evidence. S1-002 BLOCKED pending actual client execution. No S1-003 work.
