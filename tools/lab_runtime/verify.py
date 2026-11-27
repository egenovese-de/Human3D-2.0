"""Verify provisioned runtime without modifying it."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

from bootstrap import ROOT, LOCK, digest, safe

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runtime", type=Path, default=ROOT / ".lab-runtime")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--source-revision", required=True)
    p.add_argument("--group", action="append", default=[])
    a = p.parse_args()
    root = a.runtime.resolve()
    lock = json.loads(LOCK.read_text())
    system = platform.system().lower()
    cfg = lock["platforms"][system]
    env = dict(os.environ, **lock["environment"])
    env.pop("PYTHONPATH", None)
    checks = []
    def check(name, fn, required=True):
        try:
            detail = fn()
            checks.append(dict(name=name, status="PASS", required=required, detail=detail))
        except Exception as e:
            checks.append(dict(name=name, status="FAIL", required=required, detail=str(e)))
    def command(args, extra=None):
        return subprocess.check_output([str(x) for x in args], env=dict(env, **(extra or {})), stderr=subprocess.STDOUT, text=True, timeout=180).strip()
    def equal(actual, expected):
        if actual != expected:
            raise ValueError(f"expected {expected!r}, got {actual!r}")
        return actual
    py = root / "venv" / ("Scripts/python.exe" if system=="windows" else "bin/python")
    exe = root / "blender" / ("blender.exe" if system=="windows" else "blender")
    check("source_revision", lambda: equal(command(["git","-C",a.source,"rev-parse","HEAD"]), a.source_revision))
    check("source_clean", lambda: equal(command(["git","-C",a.source,"status","--porcelain","--untracked-files=no"]), ""))
    check("python", lambda: equal(command([py,"-c","import platform; print(platform.python_version())"]),lock["python"]["version"]))
    check("pip_check", lambda: command([py,"-m","pip","check"]))
    for name, version in lock["dependencies"].items():
        check("dependency:"+name, lambda n=name,v=version: equal(command([py,"-c",f"import importlib.metadata as m; print(m.version({n!r}))"]),v))
    check("dependency_lock", lambda: equal((root/"venv"/".dependency-lock").read_text(),digest(ROOT/cfg["dependency_lock"])))
    check("blender_archive", lambda: equal(digest(root/"cache"/cfg["blender_archive"]),cfg["sha256"]))
    check("blender_version", lambda: equal(command([exe,"--version"]).splitlines()[0].split()[:2],["Blender",lock["blender"]["version"]]))
    check("blender_headless", lambda: command([exe,"--background","--factory-startup","--python-exit-code","1","--python-expr","import bpy; assert bpy.app.background; assert hasattr(bpy.ops.wm, 'usd_import'); print('BPY_OK', bpy.app.version_string)"]))
    check("numerical_import", lambda: command([py,"-c","import numpy as n; import scipy.linalg as s; assert n.allclose(s.solve(n.eye(2),[1,2]),[1,2]); print('NUMERIC_OK')"]))
    check("openusd", lambda: command([py,"-c","from pxr import Usd, UsdGeom; s=Usd.Stage.CreateInMemory(); UsdGeom.Mesh.Define(s,'/Mesh'); assert s.GetPrimAtPath('/Mesh').IsValid(); print('USD_OK')"]))
    check("qt_offscreen", lambda: command([py,"-c","from PySide6.QtWidgets import QApplication; a=QApplication([]); print('QT_OK')"]))
    check("human3d", lambda: command([py,"-c","import human3d; import human3d.vision; print(human3d.__file__)"],{"PYTHONPATH":str(a.source.resolve()/"src")}))
    groups=set(a.group)
    for name,g in lock["asset_groups"].items():
        if g.get("kind")=="historical_inventory":
            continue
        required=g["required"] or name in groups
        def assets(g=g,name=name):
            m=json.loads((ROOT/g["manifest"]).read_text())
            for item in m["files"]:
                rel=m.get("source_prefix","")+item["path"]
                path=safe(root/"assets"/name,rel)
                equal(path.stat().st_size,item["bytes"])
                equal(digest(path),item["sha256"])
            return len(m["files"])
        check("assets:"+name,assets,required)
    model=root/"assets"/"pose_lite"/"pose_landmarker_lite.task"
    check("mediapipe_init",lambda: command([py,"-c","from pathlib import Path; import sys; from human3d.vision import PoseLandmarker; p=PoseLandmarker(Path(sys.argv[1]),segmentation=True); p.close(); print('POSE_OK')",model],{"PYTHONPATH":str(a.source.resolve()/"src")}))
    def output():
        dest=ROOT/lock["paths"]["outputs"]
        dest.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dest) as tmp:
            path=Path(tmp)/"probe"
            path.write_text("ok")
            equal(path.read_text(),"ok")
        free=shutil.disk_usage(dest).free
        if free<1024**3: raise ValueError("less than 1 GiB free")
        return free
    check("output_and_disk",output)
    result={"schema_version":1,"source_revision":a.source_revision,"platform":system,"checks":checks,"status":"PASS" if all(c["status"]=="PASS" or not c["required"] for c in checks) else "FAIL"}
    root.mkdir(parents=True,exist_ok=True)
    (root/"runtime_report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__":
    sys.exit(main())
