@echo off
chcp 65001 >nul
title Build OpenTutor Desktop
cd /d "%~dp0"

where pyinstaller >nul 2>nul
if errorlevel 1 goto:nopy

python make_icon.py
if errorlevel 1 goto:fail

pyinstaller --noconfirm --clean --onefile --windowed ^
  --name OpenTutor ^
  --icon app.ico ^
  --add-data "static;static" ^
  desktop.py
if errorlevel 1 goto:fail

echo.
echo Built: dist\OpenTutor.exe
goto:done

:nopy
echo [error] PyInstaller not found. Run: pip install pyinstaller
goto:fail

:fail
echo [error] build failed
pause
exit /b 1

:done
pause
