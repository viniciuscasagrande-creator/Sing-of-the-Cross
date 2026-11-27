@echo off
title SING OF THE CROSS (SOTC) - Multi-Cloud Control Center
echo =================================================================
echo   SING OF THE CROSS (SOTC) - MULTI-CLOUD INFRASTRUCTURE MONITOR
echo   Abrindo http://127.0.0.1:8765 ...
echo =================================================================
cd /d "%~dp0"
start "" "http://127.0.0.1:8765"
if exist "C:\laragon\bin\python\python-3.13\python.exe" (
    "C:\laragon\bin\python\python-3.13\python.exe" app.py
) else (
    "C:\Program Files\nodejs\node.exe" server.js
)
pause
