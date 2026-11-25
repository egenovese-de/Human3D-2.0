# Runtime baseline

Verified foundation: CPython 3.11.9 x64, Ubuntu 24.04 and Windows Server 2022 hosted runners; setuptools 75.8.2. CI run 45639961336 at 19ff2eee3483d3665f810f661cf529b0d41e8438: package install, unittest discovery and CLI version all PASS on both platforms.

Validation commands:
- `python -m pip install .`
- `python -m unittest discover -s tests -v`
- `human3d --version`

This verifies only the standard-library foundation. Scientific, vision, GUI and USD dependencies, transitive locks, Windows desktop and Blender runtime remain unverified. Admit dependencies after license and compatibility review. No D1-01 acceptance yet.
