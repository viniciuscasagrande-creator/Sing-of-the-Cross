@echo off
title Cloud VM Monitor - VS Code Dashboard
echo ===================================================
echo   Iniciando Cloud VM Monitor (Porta 8501)...
echo ===================================================
cd /d "%~dp0"
start "" "http://localhost:8501"
"C:\Program Files\nodejs\node.exe" server.js
pause
