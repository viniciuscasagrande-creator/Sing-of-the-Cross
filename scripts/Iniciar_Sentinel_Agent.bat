@echo off
title SING OF THE CROSS (SOTC) - V0.7 The Sentinel Continuous Agent
cd /d "%~dp0.."
echo =================================================================
echo   SING OF THE CROSS - V0.7 THE SENTINEL AGENT (24/7 BACKGROUND)
echo   Sincronizando telemetria SSH com Neon PostgreSQL + Vercel...
echo =================================================================
if exist "C:\laragon\bin\python\python-3.13\python.exe" (
  "C:\laragon\bin\python\python-3.13\python.exe" agent\sentinel.py
) else (
  python agent\sentinel.py
)
pause
