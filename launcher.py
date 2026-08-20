"""Launcher portable para el ejecutable Windows GEX_Dashboard.exe
Inicia el servidor GEX y abre automáticamente el navegador en http://127.0.0.1:8050.
"""
from __future__ import annotations

import sys
import os
import time
import webbrowser
import threading
from pathlib import Path

# Ajustar directorio base si se ejecuta congelado en PyInstaller
if getattr(sys, "frozen", False):
    base_dir = Path(sys.executable).parent
    os.chdir(base_dir)

from dotenv import load_dotenv
load_dotenv()

from gex.run import main

def open_browser():
    time.sleep(2.0)
    webbrowser.open("http://127.0.0.1:8050")

if __name__ == "__main__":
    print("=" * 60)
    print("  GEX DASHBOARD - INICIANDO SERVIDOR INSTITUCIONAL")
    print("=" * 60)
    print("  Acceso web : http://127.0.0.1:8050")
    print("  Presiona Ctrl + C en esta ventana para detener el servidor.")
    print("=" * 60)
    
    # Hilo para abrir el navegador automáticamente
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Iniciar servidor Dash
    main(host="127.0.0.1", port=8050)
