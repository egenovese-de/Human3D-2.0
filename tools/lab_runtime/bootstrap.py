"""Provision the locked lab runtime; no global package installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "tools/lab_runtime/runtime.lock.json"

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def safe(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("unsafe path: " + name)
    return path

def acquire(url, path, sha, size=None):
    if not sha or len(sha) != 64:
        raise ValueError("missing pinned checksum")
    if path.is_file() and digest(path) == sha and (size is None or path.stat().st_size == size):
        return "reused"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    os.close(fd)
    tmp = Path(tmp)
    try:
        with urllib.request.urlopen(url, timeout=120) as src, tmp.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        if digest(tmp) != sha or (size is not None and tmp.stat().st_size != size):
            raise ValueError("checksum or size mismatch: " + url)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return "downloaded"

def extract(archive, dest):
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        root = Path(tmp)
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                for item in z.infolist():
                    safe(root, item.filename)
                    if (item.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError("zip symlink")
                z.extractall(root)
        else:
            with tarfile.open(archive) as t:
                t.extractall(root, filter="data")
        entries = list(root.iterdir())
        if len(entries) != 1 or not entries[0].is_dir():
            raise ValueError("unexpected archive layout")
        if dest.exists():
            shutil.rmtree(dest)
        entries[0].rename(dest)

def run(args, env):
    subprocess.run([str(x) for x in args], env=env, check=True, timeout=1800)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", action="append", default=[])
    parser.add_argument("--runtime", type=Path, default=ROOT / ".lab-runtime")
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    if platform.python_version() != lock["python"]["version"]:
        raise RuntimeError("wrong Python version")
    system = platform.system().lower()
    if system not in lock["platforms"] or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("unsupported platform")
    cfg = lock["platforms"][system]
    root = args.runtime.resolve()
    root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, **lock["environment"])
    env.pop("PYTHONPATH", None)
    report = {"platform": system, "assets": [], "status": "failed"}
    try:
        dep = ROOT / cfg["dependency_lock"]
        ve = root / "venv"
        py = ve / ("Scripts/python.exe" if system == "windows" else "bin/python")
        stamp = ve / ".dependency-lock"
        key = digest(dep)
        if not py.is_file() or not stamp.is_file() or stamp.read_text() != key:
            if ve.exists():
                shutil.rmtree(ve)
            venv.EnvBuilder(with_pip=True).create(ve)
            run([py, "-m", "pip", "install", "--only-binary=:all:", "--no-deps", "--require-hashes", "-r", dep], env)
            stamp.write_text(key)
            report["venv"] = "created"
        else:
            report["venv"] = "reused"
        run([py, "-m", "pip", "check"], env)
        archive = root / "cache" / cfg["blender_archive"]
        report["archive"] = acquire(lock["blender"]["base_url"] + archive.name, archive, cfg["sha256"])
        dest = root / "blender"
        exe = dest / ("blender.exe" if system == "windows" else "blender")
        marker = dest / ".archive-sha256"
        if not exe.is_file() or not marker.is_file() or marker.read_text() != cfg["sha256"]:
            extract(archive, dest)
            marker.write_text(cfg["sha256"])
            report["blender"] = "extracted"
        else:
            report["blender"] = "reused"
        version = subprocess.check_output([str(exe), "--version"], env=env, timeout=60, text=True)
        print("Blender version output:", repr(version.splitlines()[0]), flush=True)
        if version.splitlines()[0].split()[:2] != ["Blender", lock["blender"]["version"]]:
            raise RuntimeError("Blender version mismatch: " + repr(version))
        groups = set(args.group) | {k for k,v in lock["asset_groups"].items() if v["required"]}
        for name in sorted(groups):
            group = lock["asset_groups"][name]
            if group.get("kind") == "historical_inventory":
                raise ValueError("historical assets require separate admission")
            manifest = json.loads((ROOT / group["manifest"]).read_text())
            for item in manifest["files"]:
                rel = manifest.get("source_prefix", "") + item["path"]
                url = item.get("url")
                if url is None:
                    url = "https://raw.githubusercontent.com/makehumancommunity/makehuman/" + manifest["revision"] + "/" + rel
                path = safe(root / "assets" / name, rel)
                state = acquire(url, path, item["sha256"], item.get("bytes"))
                report["assets"].append({"group":name,"path":rel,"sha256":item["sha256"],"state":state})
        report["status"] = "success"
    finally:
        (root / "bootstrap_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status":report["status"],"venv":report["venv"],"archive":report["archive"],"blender":report["blender"],"assets":len(report["assets"]),"reused":sum(a["state"]=="reused" for a in report["assets"])}))

if __name__ == "__main__":
    main()
