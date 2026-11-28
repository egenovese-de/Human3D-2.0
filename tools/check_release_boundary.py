"""Fail closed on prohibited files in tracked history and the built application wheel."""
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

DENIED = {".task",".onnx",".safetensors",".pt",".pth",".usdz",".usdc",".blend",".blend1",".obj",".mhskel",".mhw",".target",".jpg",".jpeg",".png",".webp",".heic",".zip",".whl",".dll",".so",".dylib",".exe",".pyd"}
PRIVATE = {"private","local-data","artifacts",".venv"}
# Exact historical Q render outputs. Any new bytes, new paths or reachability
# from a production ref use the ordinary prohibited-file policy.
Q_RENDER_BLOBS = {
    "DOCS/q/MBLab_human_female_asymmetric.png": "f57603001f6e1cf2df185ed8f16685c35cde4137",
    "DOCS/q/MBLab_human_male_base.png": "9c614a99a8b6ba3aeea594d2e47d90054f79d545",
    "DOCS/q/diagnostics.png": "5ff739193e268e0796f9756fbfa4d720253d82c7",
    "DOCS/q/finalization/annotation-plate.png": "3cd664f4490cb8d0f12c5b3a45858d8b586c9819",
    "DOCS/q/followup/articulation-atlas.png": "7e248e26f8e9d0ff2bb337539e7eff91fb781201",
    "DOCS/q/followup/layered-atlas.png": "5e5ba42a89ca5dcb0c941af81bebda07f7697b60",
    "DOCS/q/holdout_atlas.png": "2b6834e0d80bd26654c482d0fe84e0f5bfbc0e53",
    "lab/fixtures/x-vlm/front.jpg": "14369064d52fbaf0146e71df617e551d95c94e3e",
    "lab/fixtures/x-vlm/side.jpg": "15ff5a4da911aeafa4b4db0aa3312806d5850d07",
    "lab/fixtures/x-vlm/threequarter.jpg": "ded4b1d4fc2cad5a75dc1f715b4d555970674bf5",
}
LAB_REFS = {
    prefix + branch for prefix in ("refs/heads/", "refs/remotes/origin/") for branch in
    ("lab/render", "lab/g1-makehuman", "lab/g2-photographic-evidence",
     "lab/g3-camera-registration", "lab/g4-anatomical-fitting")
}


def prohibited(name):
    path = PurePosixPath(name)
    return (path.suffix.lower() in DENIED or any(p.lower() in PRIVATE for p in path.parts)
            or any(p.lower()==".env" or p.lower().startswith(".env.") for p in path.parts))

def _git(*args):
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8", errors="surrogateescape")


def _historical_asset_allowed(name, object_id, *, lab_only):
    return lab_only and Q_RENDER_BLOBS.get(name) == object_id


def _audit_history():
    refs = _git("for-each-ref", "--format=%(refname)").splitlines()
    lab_refs = [ref for ref in refs if ref in LAB_REFS]
    other_refs = [ref for ref in refs if ref not in LAB_REFS]
    # Lab blobs must still be denied if a release, tag or other branch
    # contains them, even when the blob was first published in Lab.
    head_ref = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], capture_output=True, text=True)
    if head_ref.stdout.strip() not in LAB_REFS:
        other_refs.append("HEAD")
    protected = set(_git("rev-list", *other_refs).splitlines()) if other_refs else set()
    lab = set(_git("rev-list", *lab_refs).splitlines()) if lab_refs else set()
    commits = set(_git("rev-list", "--all", "HEAD").splitlines())
    for commit in sorted(commits):
        entries = _git("ls-tree", "-r", "-z", commit).split("\0")
        for entry in entries:
            if not entry:
                continue
            metadata, _, name = entry.partition("\t")
            if not prohibited(name):
                continue
            object_id = metadata.split()[2]
            if not _historical_asset_allowed(name, object_id, lab_only=commit in lab and commit not in protected):
                raise SystemExit("Prohibited asset path in reachable commit " + commit)
    return len(commits)


def main():
    print(f"PASS: {_audit_history()} reachable trees screened", flush=True)
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
