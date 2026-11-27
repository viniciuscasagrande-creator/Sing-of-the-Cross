@echo off
title SING OF THE CROSS (SOTC) - V0.6 The Reaper + V0.6.5 The Convergence
cd /d "%~dp0"
echo =================================================================
echo   SING OF THE CROSS - V0.6 THE REAPER + DEVCENTRAL CONVERGENCE
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
