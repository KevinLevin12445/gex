@echo off
cd /d "%~dp0"
echo ======================================================
echo   Compilando GEX Dashboard a ejecutable (.exe)...
echo ======================================================
.\.venv\Scripts\pyinstaller.exe --clean -y GEX_Dashboard.spec
if %ERRORLEVEL% EQU 0 (
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
