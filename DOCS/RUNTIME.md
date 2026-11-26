# Runtime baseline

Verified foundation: CPython 3.11.9 x64, Ubuntu 24.04 and Windows Server 2022 hosted runners; setuptools 75.8.2. CI run 45639961336 at 19ff2eee3483d3665f810f661cf529b0d41e8438: package install, unittest discovery and CLI version all PASS on both platforms.

Validation commands:
- `python -m pip install .`
- `python -m unittest discover -s tests -v`
- `human3d --version`

This verifies only the standard-library foundation. Scientific, vision, GUI and USD dependencies, transitive locks, Windows desktop and Blender runtime remain unverified. Admit dependencies after license and compatibility review. No D1-01 acceptance yet.

## Dependency probe
CI 45640171337 at 125655489d4626ab7ec69d24811f7bda786de433: both platforms PASS binary installation, pip check and imports. Candidate platform locks capture 32 packages each; only fonttools differs (Linux 4.69.0, Windows 4.68.0). These are observed version pins, not hash-verified locks. PySide6 LGPL compliance and bundled native libraries require review before distribution. No bundled wheels admitted. Blender and desktop validation remain open.

## Runtime verification checkpoint
Locked candidate runtime passed Windows and Linux in run 45640810469, including Qt offscreen and OpenUSD in-memory stage. Linux requires libegl1, libgl1 and libglib2.0-0t64. Blender 4.5.3 LTS Windows archive verified against official SHA-256 and actual triangle USD import passed in run 45641459520. Wheel digest run 45641693982 produced 31 hashes per platform; requirements-linux.lock and requirements-windows.lock now pin exact wheel digests. Hash-enforced reinstall is pending final CI evidence. Earlier counts of 32 were incorrect. This is not a rigged USD or interactive desktop acceptance test.

Hash-enforced installation and Qt/OpenUSD smoke tests passed on both platforms in run 45641848574. D1-01 local evidence and branch required-check configuration remain to be confirmed.


## RC1 stabilization dependency contract (S1-001)
The historical checkpoints above are not current installation instructions. Production direct pins in pyproject.toml are authoritative; requirements-linux.lock and requirements-windows.lock are the supported hash-pinned runtime resolutions (24 packages each, fonttools is the sole version difference). Candidate files are exploratory mirrors, not supported install inputs. Historical candidate resolution remains available at M5 a7f297806f6b2b6b2d51caa61565fbc9b2cc273a. No production version or hash changed. The seven historical candidate-only packages attrs, jax, jaxlib, ml-dtypes, opt-einsum, protobuf and sentencepiece are absent from the validated production resolution.

Use fresh CPython 3.11 x64 environment; install platform lock with python -m pip install --only-binary=:all: --require-hashes --no-deps -r requirements-PLATFORM.lock (replace PLATFORM with linux or windows), then python -m pip install --no-deps . and python -m pip check. Build isolation still resolves setuptools separately; fully offline/reproducible build is not certified here. Run python -m unittest discover -s tests -v and human3d --version. The dependency contract tests check normalized direct pins, both mirrors, hash syntax, duplicates, platform differences, installed versions and native imports/USD smoke. Windows 11 local validation belongs to S1-002; workflow consolidation S4-002; licensing/security S1-004. CI evidence pending for the new tests.

S1-001 final CI evidence: run 45783389414 at 31f91a50032bf7c0da236222a641ff127451af64 completed successfully; 37/37 tests on each platform, including all three dependency contract tests. Ubuntu 2.417s, Windows 7.440s. Production dependency versions and hashes unchanged. S1-001 DONE; no Windows 11 local acceptance claimed.
