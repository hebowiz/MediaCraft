@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv\Scripts\pythonw.exe"
set "LIBMPV_DLL=%PROJECT_DIR%vendor\mpv\libmpv-2.dll"

if not exist "%PYTHON_EXE%" (
    echo MediaCraft virtual environment was not found.
    echo.
    echo Run the following commands first:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "%LIBMPV_DLL%" (
    echo libmpv was not found.
    echo.
    echo Run the following command first:
    echo   .venv\Scripts\python.exe scripts\setup_mpv.py
    pause
    exit /b 1
)

if /i "%~1"=="--check" (
    echo MediaCraft launcher is ready.
    exit /b 0
)

pushd "%PROJECT_DIR%"
start "" "%PYTHON_EXE%" -m mediacraft
set "START_RESULT=%ERRORLEVEL%"
popd

exit /b %START_RESULT%
