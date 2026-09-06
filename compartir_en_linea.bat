@echo off
cd /d "%~dp0"
echo ============================================================
echo   Iniciando GEX Dashboard y Enlace Publico en Linea
echo ============================================================
echo.
.\.venv\Scripts\python.exe launcher.py
pause
