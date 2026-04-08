@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   MediaGrab - Windows Build Script
echo ============================================
echo.

echo [1/5] Installing Python dependencies...
pip install -r requirements.txt
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)
echo.

echo [2/5] Building PyInstaller executable...
pyinstaller --noconfirm --onefile --windowed --name "MediaGrab" --add-data "assets;assets" --add-data "../VERSION;." --add-data "../shared;shared" --hidden-import "customtkinter" --hidden-import "yt_dlp" --hidden-import "PIL" --hidden-import "requests" --hidden-import "psutil" --collect-all "yt_dlp" main.py
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)
echo PyInstaller build complete.
echo.

echo [3/5] Preparing distribution folder...
set "STAGING=dist\installer_staging"
if exist "!STAGING!" rmdir /s /q "!STAGING!"
mkdir "!STAGING!"
mkdir "!STAGING!\assets"
mkdir "!STAGING!\ffmpeg"

if exist "dist\MediaGrab.exe" (
    copy /Y "dist\MediaGrab.exe" "!STAGING!\MediaGrab.exe"
) else if exist "build\MediaGrab\MediaGrab.exe" (
    copy /Y "build\MediaGrab\MediaGrab.exe" "!STAGING!\MediaGrab.exe"
) else (
    echo ERROR: MediaGrab.exe not found after PyInstaller build.
    exit /b 1
)

if exist "assets\" (
    xcopy /E /I /Y "assets" "!STAGING!\assets"
)

if exist "ffmpeg\bin\ffmpeg.exe" (
    xcopy /E /I /Y "ffmpeg" "!STAGING!\ffmpeg"
    echo FFmpeg binaries copied.
) else (
    echo WARNING: FFmpeg binaries not found.
    echo To bundle FFmpeg, place ffmpeg.exe in desktop\ffmpeg\bin\
)
echo.

echo [4/5] Building Inno Setup installer...
set "ISCC="
where iscc >nul 2>nul && set "ISCC=iscc"

if "!ISCC!"=="" (
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if "!ISCC!"=="" (
    if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if "!ISCC!"=="" (
    echo WARNING: Inno Setup compiler not found.
    echo PyInstaller executable built successfully at dist\MediaGrab.exe
    echo Install Inno Setup 6 from https://jrsoftware.org/isinfo.php to build installer.
    goto summary
)

echo Found Inno Setup: !ISCC!
cd /d "%~dp0"
"!ISCC!" installer_windows.iss
if !ERRORLEVEL! EQU 0 (
    echo Installer build successful!
) else (
    echo ERROR: Inno Setup compilation failed.
)
echo.

:summary
echo [5/5] Build Summary
echo ============================================
if exist "!STAGING!\MediaGrab.exe" (
    echo [OK] MediaGrab.exe (PyInstaller)
) else (
    echo [FAIL] MediaGrab.exe not found
)

set "FOUND_INSTALLER=0"
for %%f in (dist\MediaGrab-*-Setup.exe) do (
    if exist "%%f" set "FOUND_INSTALLER=1"
)
if "!FOUND_INSTALLER!"=="1" (
    echo [OK] MediaGrab Setup Installer
) else (
    echo [--] Setup Installer not built
)
echo ============================================
echo.
