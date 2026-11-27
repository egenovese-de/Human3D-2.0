# Install the M6 development build

The development wheel was built twice with identical bytes from `1c46f93500486c9b356fa6bbfb14e6f61a942b77`. Its package name is `human3d-0.2.0-py3-none-any.whl`, and its SHA-256 is `b0af2dd6aac0e4a1a68c2c6fec432cf10d7b74864a34f58b189af7c0b7691daf`. The package version remains 0.2.0 until the v0.3.0 technical gates pass.

Start in a checkout of the candidate commit, with Python 3.11.9. Put the verified wheel in the checkout directory.

## Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-windows.lock
.\.venv\Scripts\python.exe -m pip install --no-deps .\human3d-0.2.0-py3-none-any.whl
.\.venv\Scripts\human3d.exe --version
.\.venv\Scripts\human3d-desktop.exe
```

## Linux

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-linux.lock
.venv/bin/python -m pip install --no-deps ./human3d-0.2.0-py3-none-any.whl
.venv/bin/human3d --version
.venv/bin/human3d-desktop
```

Use the approved local MakeHuman assets and optional pose model from the [stabilization installation guide](STABILIZATION_INSTALL.md). The application-only wheel contains neither asset type. Follow the existing runtime library prerequisites for Linux.
