@echo off
REM One-shot build: portable app + (if Inno Setup present) installer exe.
REM (c) 2026 Renufus
setlocal
cd /d "%~dp0\.."

echo [1/4] Generate icon...
python packaging\make_icon.py || goto :err

echo [2/4] Ensure Playwright browsers are installed...
python -m playwright install || goto :err

echo [3/5] PyInstaller bundle (large - bundles all browsers)...
pip install --quiet pyinstaller pillow cx_Freeze || goto :err
pyinstaller --noconfirm --clean MultiBrowserLauncher.spec || goto :err

echo [4/5] Installer .exe (Inno Setup)...
where iscc >nul 2>nul
if %errorlevel%==0 (
  iscc packaging\installer.iss || goto :err
  echo   DONE -^> dist\MultiBrowserLauncher-Setup.exe
) else (
  echo   Inno Setup not found - skipping .exe. Portable build:
  echo     dist\MultiBrowserLauncher\MultiBrowserLauncher.exe
  echo   Install Inno Setup ^(https://jrsoftware.org^) then: iscc packaging\installer.iss
)

echo [5/5] Installer .msi (cx_Freeze, no extra tools needed)...
python setup_msi.py bdist_msi || goto :err
echo   DONE -^> dist\*.msi
goto :eof

:err
echo BUILD FAILED
exit /b 1
