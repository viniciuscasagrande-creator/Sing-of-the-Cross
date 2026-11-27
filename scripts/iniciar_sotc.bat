@echo off
title SIGN OF THE CROSS (SOTC) - Multi-Cloud Command Center & Flight Deck
cd /d "%~dp0.."
echo =================================================================
echo   SIGN OF THE CROSS - MULTI-CLOUD COMMAND CENTER & FLIGHT DECK
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
