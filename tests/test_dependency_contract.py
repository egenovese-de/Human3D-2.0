"""Verify the production dependency contract and historical mirror consistency."""
import importlib.metadata
import re
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def pins(path, hashed=False):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pattern = r"([A-Za-z0-9_.-]+)==([^\s]+)"
        if hashed:
            pattern += r" --hash=sha256:[0-9a-f]{64}"
        match = re.fullmatch(pattern, line)
        if not match:
            raise ValueError(f"Invalid pin: {path.name}: {line}")
        name = re.sub(r"[-_.]+", "-", match[1]).lower()
        if name in result:
            raise ValueError(f"Duplicate pin: {name}")
        result[name] = match[2]
    return result

class DependencyContractTests(unittest.TestCase):
    def test_direct_and_platform_pins(self):
        project = tomllib.loads((ROOT/"pyproject.toml").read_text(encoding="utf-8"))
        direct = {}
        for item in project["project"]["dependencies"]:
            name, version = item.split("==")
            direct[re.sub(r"[-_.]+", "-", name).lower()] = version
        self.assertEqual(direct, pins(ROOT/"requirements-candidate.txt"))
        for platform in ("linux", "windows"):
            locked = pins(ROOT/f"requirements-{platform}.lock", True)
            self.assertEqual(locked, pins(ROOT/f"requirements-{platform}.candidate.lock"))
            self.assertEqual(direct, {name: locked[name] for name in direct})
        linux = pins(ROOT/"requirements-linux.lock", True)
        windows = pins(ROOT/"requirements-windows.lock", True)
        self.assertEqual(linux.keys(), windows.keys())
        self.assertEqual({k for k in linux if linux[k] != windows[k]}, {"fonttools"})

    def test_installed_production_versions(self):
        platform = {"win32":"windows", "linux":"linux"}.get(sys.platform)
        if platform is None:
            self.skipTest("No supported platform lock")
        for name, version in pins(ROOT/f"requirements-{platform}.lock", True).items():
            with self.subTest(name=name):
                self.assertEqual(importlib.metadata.version(name), version)

    def test_native_imports_and_usd(self):
        import numpy
        import scipy
        import PIL
        import mediapipe
        from PySide6 import QtCore
        from pxr import Usd
        self.assertTrue(Usd.Stage.CreateInMemory())
        self.assertEqual(QtCore.qVersion(), "6.8.3")
