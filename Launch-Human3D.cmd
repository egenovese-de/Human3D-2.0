@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto setup
if not exist "local-data\m7-ready.txt" goto setup
set "HUMAN3D_ROOT=%CD%"
set "PYTHONPATH=%CD%\src"
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set /p HUMAN3D_REVISION=< "local-data\m7-ready.txt"
if exist "M7-REVISION.txt" set /p HUMAN3D_REVISION=< "M7-REVISION.txt"
if not exist "M7-REVISION.txt" for /f %%R in ('git rev-parse HEAD 2^>nul') do set "HUMAN3D_REVISION=%%R"
".venv\Scripts\python.exe" -m human3d.empirical_desktop > "local-data\m7-launch.log" 2>&1
if errorlevel 1 (
    echo Human3D could not start or terminated unexpectedly. See local-data\m7-launch.log.
    type "local-data\m7-launch.log"
    pause
    exit /b 1
)
exit /b 0

:setup
echo Run Setup-Human3D.ps1 first. See DOCS\M7_WINDOWS_INSTALL.md.
pause
exit /b 1
