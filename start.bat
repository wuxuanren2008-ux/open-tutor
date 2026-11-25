@echo off
chcp 65001 >nul
title OpenTutor
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 goto:usepy
where py >nul 2>nul
if %errorlevel%==0 goto:usepy3
echo [错误] 未找到 Python，请先安装 Python 3.8+ 并加入 PATH。
pause
exit /b 1

:usepy
python start.py
goto:done

:usepy3
py -3 start.py
goto:done

:done
pause
