"""Build twice from an exact Git revision and publish the verified application wheel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    revision = git("rev-parse", "HEAD")
    timestamp = git("show", "-s", "--format=%ct", revision)
    env = dict(os.environ, SOURCE_DATE_EPOCH=timestamp, PYTHONHASHSEED="0")
    with TemporaryDirectory(prefix="human3d-wheel-") as temporary:
        directory = Path(temporary)
        archive = directory / "source.zip"
        git("archive", "--format=zip", f"--output={archive}", revision)
        wheels = []
        for index in range(2):
            source = directory / f"source-{index}"
            output = directory / f"dist-{index}"
            with ZipFile(archive) as bundle:
                bundle.extractall(source)
            subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps",
                            "--wheel-dir", str(output), "."], cwd=source, env=env, check=True)
            wheel, = output.glob("*.whl")
            wheels.append(wheel)
        first, second = wheels
        sha256 = digest(first)
        if first.name != second.name or sha256 != digest(second):
            raise RuntimeError("Independent wheel builds differ")
        subprocess.run([sys.executable, str(ROOT / "tools/check_release_boundary.py"),
                        str(first.parent)], cwd=ROOT, check=True)
        args.output.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(first, args.output / first.name)
    print("VERIFIED_WHEEL " + json.dumps({
        "revision": revision, "source_date_epoch": int(timestamp),
        "wheel": first.name, "sha256": sha256,
    }), flush=True)


if __name__ == "__main__":
    main()
