"""Package only the exact M7 source revision and installation inputs."""
import argparse
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from human3d import __version__

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ("src", "DOCS", "tools/provision_m7_assets.py", "requirements-windows.lock",
           "LICENSE", "README.md", "pyproject.toml", "Setup-Human3D.ps1", "Launch-Human3D.cmd")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def package(output):
    revision = git("rev-parse", "HEAD")
    name = f"Human3D-{__version__}-windows-{revision[:12]}"
    output.mkdir(parents=True, exist_ok=True)
    target = output / (name + ".zip")
    with TemporaryDirectory() as directory:
        source = Path(directory) / "source.zip"
        subprocess.run(["git", "archive", "--format=zip", f"--output={source}", revision,
                        *INCLUDE], cwd=ROOT, check=True)
        with ZipFile(source) as original, ZipFile(target, "w", ZIP_DEFLATED) as archive:
            for member in original.infolist():
                if not member.is_dir():
                    archive.writestr(f"{name}/{member.filename}", original.read(member))
            archive.writestr(f"{name}/M7-REVISION.txt", revision + "\n")
        with ZipFile(target) as archive:
            if archive.testzip() or archive.read(f"{name}/M7-REVISION.txt").decode().strip() != revision:
                raise RuntimeError("Distribution integrity check failed.")
    print(target.resolve())
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    package(parser.parse_args().output)
