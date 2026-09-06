"""Launcher portable para el ejecutable Windows GEX_Dashboard.exe
Inicia el servidor GEX y el túnel Cloudflare para acceso público en línea.
"""
from __future__ import annotations

import atexit
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ajustar directorio base si se ejecuta congelado en PyInstaller
if getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).resolve().parent
    # Si el ejecutable está en dist/GEX_Dashboard/ o dist/ dentro del repositorio
    if (exe_dir.parent.parent / "pyproject.toml").exists() and (exe_dir.parent.parent / "data").exists():
        base_dir = exe_dir.parent.parent
    elif (exe_dir.parent / "pyproject.toml").exists() and (exe_dir.parent / "data").exists():
        base_dir = exe_dir.parent
    else:
        base_dir = exe_dir
    os.chdir(base_dir)
else:
    base_dir = Path(__file__).resolve().parent
    exe_dir = base_dir

from dotenv import load_dotenv
load_dotenv()

from gex.run import main

_cf_proc: subprocess.Popen | None = None


def _find_cloudflared() -> Path | None:
    """Busca cloudflared.exe en ubicaciones estándar del proyecto o el sistema."""
    candidates = [
        base_dir / ".tools" / "cloudflared.exe",
        exe_dir / ".tools" / "cloudflared.exe",
        exe_dir / "_internal" / ".tools" / "cloudflared.exe",
        exe_dir / "cloudflared.exe",
        base_dir / "cloudflared.exe",
    ]
    for p in candidates:
        if p.is_file():
            return p
    which = shutil.which("cloudflared")
    if which:
        return Path(which)
    return None


def _copy_to_clipboard(text: str) -> None:
    """Copia texto al portapapeles de Windows de forma silenciosa."""
    try:
        subprocess.run(
            "clip",
            input=text.strip(),
            text=True,
            shell=True,
            capture_output=True,
            timeout=2,
        )
    except Exception:
        pass


def _kill_cloudflared() -> None:
    """Termina el proceso del túnel al cerrar."""
    global _cf_proc
    if _cf_proc is not None:
        try:
            _cf_proc.terminate()
            _cf_proc.wait(timeout=2)
        except Exception:
            try:
                _cf_proc.kill()
            except Exception:
                pass
        _cf_proc = None


atexit.register(_kill_cloudflared)


def start_tunnel_and_browser() -> None:
    """Inicia el túnel de Cloudflare y abre el enlace en el navegador."""
    global _cf_proc
    time.sleep(1.5)  # Esperar que Dash empiece a escuchar
    cf_path = _find_cloudflared()

    if not cf_path:
        print("\n  [INFO] cloudflared.exe no encontrado. Modo local activo.")
        print("  Acceso web: http://127.0.0.1:8050\n")
        webbrowser.open("http://127.0.0.1:8050")
        return

    print("  [CLOUDFLARE] Creando enlace público seguro con Cloudflare...")
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        _cf_proc = subprocess.Popen(
            [str(cf_path), "tunnel", "--url", "http://127.0.0.1:8050"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creation_flags,
        )

        public_url = None
        start_time = time.time()
        for line in _cf_proc.stdout:
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                public_url = match.group(0)
                break
            if time.time() - start_time > 20:
                break

        if public_url:
            _copy_to_clipboard(public_url)
            print()
            print("=" * 70)
            print("  🚀 GEX DASHBOARD - EN LÍNEA (CLOUDFLARE)")
            print("=" * 70)
            print(f"  🌐 Enlace público : {public_url}")
            print("  📋 [OK] ¡Enlace copiado automáticamente a tu portapapeles!")
            print("  💻 Acceso local   : http://127.0.0.1:8050")
            print("=" * 70)
            print("  * Puedes abrir el enlace desde tu celular o compartirlo.")
            print("  * Para cerrar la sesión y apagar el enlace, cierra esta ventana.")
            print("=" * 70)
            print()
            webbrowser.open(public_url)
        else:
            print("  [AVISO] No se pudo obtener enlace público a tiempo. Abriendo local...")
            webbrowser.open("http://127.0.0.1:8050")

    except Exception as e:
        print(f"  [ERROR Cloudflare] {e}. Abriendo local...")
        webbrowser.open("http://127.0.0.1:8050")


if __name__ == "__main__":
    print("=" * 70)
    print("  GEX DASHBOARD - INICIANDO SISTEMA INSTITUCIONAL")
    print("=" * 70)
    print("  Servidor local: http://127.0.0.1:8050")
    print("  Conectando túnel Cloudflare en segundo plano...")
    print("=" * 70)

    # Iniciar túnel Cloudflare y apertura de navegador en hilo secundario
    threading.Thread(target=start_tunnel_and_browser, daemon=True).start()

    try:
        main(host="127.0.0.1", port=8050)
    finally:
        _kill_cloudflared()
