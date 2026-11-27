@echo off
title SING OF THE CROSS (SOTC) - Dark Gothic Cinematic Edition (V0.5 The Guardian)
cd /d "%~dp0"
echo =================================================================
echo   SING OF THE CROSS - DARK GOTHIC CINEMATIC EDITION (V0.5)
echo   URL: http://127.0.0.1:8765
echo =================================================================
start "" "http://127.0.0.1:8765"
if exist "C:\laragon\bin\python\python-3.13\python.exe" (
  "C:\laragon\bin\python\python-3.13\python.exe" app.py
) else (
  where py >nul 2>nul
  if errorlevel 1 (
    python app.py
  ) else (
    py -3 app.py
  )
)
pause
