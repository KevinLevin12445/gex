@echo off
cd /d "%~dp0"
echo ======================================================
echo   Compilando GEX Dashboard a ejecutable (.exe)...
echo ======================================================
.\.venv\Scripts\python.exe -m PyInstaller --clean -y GEX_Dashboard.spec
if %ERRORLEVEL% EQU 0 (
    if not exist "dist\GEX_Dashboard\.tools" mkdir "dist\GEX_Dashboard\.tools"
    if exist ".tools\cloudflared.exe" copy /y ".tools\cloudflared.exe" "dist\GEX_Dashboard\.tools\cloudflared.exe" >nul
    if exist ".tools\ngrok.exe" copy /y ".tools\ngrok.exe" "dist\GEX_Dashboard\.tools\ngrok.exe" >nul
    echo.
    echo ======================================================
    echo   [OK] Compilacion completada con exito!
    echo   El ejecutable esta en: dist\GEX_Dashboard\GEX_Dashboard.exe
    echo ======================================================
) else (
    echo.
    echo [ERROR] Ocurrio un problema durante la compilacion.
)
pause
