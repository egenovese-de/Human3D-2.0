"""Clean runtime installation probe; run with CPython 3.11 x64 from a checkout."""
import argparse
import json
import os
import platform
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SMOKE = """
import os, tempfile
from pathlib import Path
import numpy as np
from scipy.linalg import solve
from PIL import Image
import mediapipe
from mediapipe.tasks.python.vision import PoseLandmarker
from PySide6.QtWidgets import QApplication
from pxr import Usd, UsdGeom
from human3d.desktop import PhotosWindow
assert np.allclose(solve(np.eye(2), [1.,2.]), [1.,2.])
app = QApplication([])
window = PhotosWindow()
window.show()
app.processEvents()
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    Image.new('RGB',(32,32)).save(p/'probe.png')
    with Image.open(p/'probe.png') as im:
        im.load()
        assert im.size == (32,32)
    stage = Usd.Stage.CreateNew(str(p/'probe.usdc'))
    UsdGeom.Xform.Define(stage, '/Probe')
    stage.GetRootLayer().Save()
    assert Usd.Stage.Open(str(p/'probe.usdc')).GetPrimAtPath('/Probe')
window.close()
print('Native runtime smoke PASS', flush=True)
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-windows11", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3,11) or struct.calcsize("P") != 8:
        raise SystemExit("CPython 3.11 x64 required")
    if sys.platform != "win32":
        raise SystemExit("Windows required")
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
        installation = winreg.QueryValueEx(key, "InstallationType")[0]
        build = int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
    windows11 = installation == "Client" and build >= 22000
    report = {"os":platform.platform(), "installation_type":installation,
              "build":build, "windows11_client":windows11,
              "python":sys.version, "status":"FAIL", "steps":[]}
    def run(label, *cmd, cwd=ROOT, env=None):
        print(label, flush=True)
        subprocess.run([str(x) for x in cmd], cwd=cwd, env=env, check=True)
        report["steps"].append(label)
    try:
        if args.require_windows11 and not windows11:
            raise RuntimeError("Windows 11 client required; server evidence is not equivalent")
        with tempfile.TemporaryDirectory(prefix="human3d-clean-") as tmp:
            venv = Path(tmp)/"venv"
            run("fresh venv", sys.executable,"-m","venv",venv)
            py = venv/"Scripts"/"python.exe"
            run("hashed binary dependencies",py,"-m","pip","install","--only-binary=:all:","--require-hashes","--no-deps","-r",ROOT/"requirements-windows.lock")
            run("application install",py,"-m","pip","install","--no-deps",ROOT)
            run("pip check",py,"-m","pip","check")
            run("installed CLI",venv/"Scripts"/"human3d.exe","--version",cwd=tmp)
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
            env.pop("PYTHONPATH",None)
            run("installed native smoke",py,"-I","-c",SMOKE,cwd=tmp,env=env)
            run("regression suite",py,"-m","unittest","discover","-s",ROOT/"tests","-v",cwd=tmp,env=env)
        report["status"]="PASS"
    finally:
        print(json.dumps(report,indent=2),flush=True)
        if args.report:
            args.report.write_text(json.dumps(report,indent=2),encoding="utf-8")

if __name__ == "__main__":
    main()
