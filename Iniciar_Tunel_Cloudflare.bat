@echo off
title SING OF THE CROSS (SOTC) - Cloudflare Zero-Trust Tunnel (Opcao 2)
cd /d "%~dp0"
echo =================================================================
echo   SING OF THE CROSS - CLOUDFLARE TUNNEL PARA O COCKPIT LOCAL
echo   Tunelando http://127.0.0.1:8765 via HTTPS seguro...
echo =================================================================
where cloudflared >nul 2>nul
if errorlevel 1 (
  if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:8765
  ) else (
    echo [AVISO] O binario cloudflared.exe nao foi encontrado no PATH.
    echo Instale com: winget install --id Cloudflare.cloudflared
  )
) else (
  cloudflared tunnel --url http://127.0.0.1:8765
)
pause
