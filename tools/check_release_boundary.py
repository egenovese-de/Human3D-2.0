"""Fail closed on prohibited files in tracked history and the built application wheel."""
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

DENIED = {".task",".onnx",".safetensors",".pt",".pth",".usdz",".usdc",".blend",".blend1",".obj",".mhskel",".mhw",".target",".jpg",".jpeg",".png",".webp",".heic",".zip",".whl",".dll",".so",".dylib",".exe",".pyd"}
PRIVATE = {"private","local-data","artifacts",".venv"}
def prohibited(name):
    path = PurePosixPath(name)
    return (path.suffix.lower() in DENIED or any(p.lower() in PRIVATE for p in path.parts)
            or any(p.lower()==".env" or p.lower().startswith(".env.") for p in path.parts))

def main():
    commits = subprocess.check_output(["git","rev-list","HEAD"],text=True).splitlines()
    for commit in commits:
        paths = subprocess.check_output(["git","ls-tree","-r","--name-only","-z",commit]).decode().split("\0")
        if any(prohibited(p) for p in paths if p):
            raise SystemExit("Prohibited asset path in reachable commit "+commit)
    print(f"PASS: {len(commits)} candidate ancestor trees screened",flush=True)
    if len(sys.argv)>1:
        for wheel in Path(sys.argv[1]).glob("*.whl"):
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
                for name in names:
                    path = PurePosixPath(name)
                    if prohibited(name) or not (path.parts[0]=="human3d" and path.suffix==".py" or path.parts[0].endswith(".dist-info")):
                        raise SystemExit("Unexpected wheel member")
                assert any(n.endswith("/LICENSE") or n.endswith("/licenses/LICENSE") for n in names)
                print("PASS: application-only wheel and license",flush=True)
        if not list(Path(sys.argv[1]).glob("*.whl")):
            raise SystemExit("No wheel found")

if __name__=="__main__":
    main()
