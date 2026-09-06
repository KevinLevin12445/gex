@echo off
cd /d "%~dp0"
echo ============================================================
echo   Iniciando Enlace Publico en Linea (Cloudflare Tunnel)
echo   Destino local: http://127.0.0.1:8050
echo ============================================================
echo.
echo Copia el enlace *.trycloudflare.com que aparecera abajo:
echo.
.\.tools\cloudflared.exe tunnel --url http://127.0.0.1:8050
pause
