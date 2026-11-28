[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$local = Join-Path $PSScriptRoot 'local-data'
$null = New-Item -ItemType Directory -Force -Path $local
Start-Transcript -Path (Join-Path $local 'm7-setup.log') -Force
try {
    function Confirm-Exit([string]$Step) {
        if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE). See local-data\m7-setup.log." }
    }
    if (-not (Get-Command 'py' -ErrorAction SilentlyContinue)) {
        throw 'Install 64-bit Python 3.11.9 with the Windows Python launcher, then run setup again.'
    }
    & py -3.11 -c "import struct,sys; sys.exit(0 if sys.version_info[:3] == (3,11,9) and struct.calcsize('P') == 8 else 1)"
    Confirm-Exit 'Python 3.11.9 x64 verification'
    $venv = Join-Path $PSScriptRoot '.venv'
    $python = Join-Path $venv 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        & py -3.11 -m venv $venv
        Confirm-Exit 'Virtual environment creation'
    }
    & $python -c "import struct,sys; sys.exit(0 if sys.version_info[:3] == (3,11,9) and struct.calcsize('P') == 8 else 1)"
    Confirm-Exit 'Existing .venv Python 3.11.9 x64 verification'
    & $python -m pip install --require-hashes --only-binary=:all: --no-deps -r requirements-windows.lock
    Confirm-Exit 'Pinned dependency installation'
    & $python -m pip check
    Confirm-Exit 'Dependency compatibility check'
    $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
    $env:HUMAN3D_ROOT = $PSScriptRoot
    $env:OPENBLAS_NUM_THREADS = '1'
    $env:OMP_NUM_THREADS = '1'
    $runtime = Join-Path $local 'm7-runtime'
    & $python tools/provision_m7_assets.py $runtime
    Confirm-Exit 'Runtime asset provisioning'
    & $python -c "from pathlib import Path; from human3d.vision import _NativePoseLandmarker; detector = _NativePoseLandmarker(Path('local-data/m7-runtime/pose.task'), segmentation=True); detector.close()"
    Confirm-Exit 'MediaPipe CPU initialization'
    $stamp = Join-Path $PSScriptRoot 'M7-REVISION.txt'
    if (Test-Path -LiteralPath $stamp) {
        $revision = (Get-Content -LiteralPath $stamp -Raw).Trim()
    } else {
        $revision = (& git rev-parse HEAD).Trim()
        Confirm-Exit 'Source revision verification'
    }
    if ($revision -cnotmatch '^[0-9a-f]{40}$') { throw 'Invalid source revision stamp.' }
    $env:HUMAN3D_REVISION = $revision
    & $python -m human3d.empirical_desktop --assets $runtime --smoke (Join-Path $local 'm7-startup.png')
    Confirm-Exit 'Desktop startup smoke test'
    Set-Content -LiteralPath (Join-Path $local 'm7-ready.txt') -Value $revision -Encoding ASCII
    Write-Host 'Setup complete. Run Launch-Human3D.cmd.'
} catch {
    Write-Host $_ -ForegroundColor Red
    exit 1
} finally {
    Stop-Transcript
}
