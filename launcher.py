"""Launcher portable para el ejecutable Windows GEX_Dashboard.exe
Inicia el servidor GEX y el túnel en línea (ngrok con dominio fijo permanente o Cloudflare).
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

_tunnel_proc: subprocess.Popen | None = None


def _find_binary(name: str) -> Path | None:
    """Busca un ejecutable en .tools, dist, _internal o PATH."""
    exe_name = f"{name}.exe" if os.name == "nt" and not name.endswith(".exe") else name
    candidates = [
        base_dir / ".tools" / exe_name,
        exe_dir / ".tools" / exe_name,
        exe_dir / "_internal" / ".tools" / exe_name,
        exe_dir / exe_name,
        base_dir / exe_name,
        Path(os.environ.get("LOCALAPPDATA", "")) / "ngrok" / exe_name if name.startswith("ngrok") else None,
    ]
    for p in candidates:
        if p and p.is_file():
            return p
    which = shutil.which(name)
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


def _kill_tunnel() -> None:
    """Termina el proceso del túnel al cerrar."""
    global _tunnel_proc
    if _tunnel_proc is not None:
        try:
            _tunnel_proc.terminate()
            _tunnel_proc.wait(timeout=2)
        except Exception:
            try:
                _tunnel_proc.kill()
            except Exception:
                pass
        _tunnel_proc = None


atexit.register(_kill_tunnel)


def start_tunnel_and_browser() -> None:
    """Inicia el túnel (ngrok permanente o Cloudflare) y abre el navegador."""
    global _tunnel_proc
    time.sleep(1.5)  # Esperar que Dash empiece a escuchar

    ngrok_token = os.getenv("NGROK_AUTHTOKEN")
    ngrok_domain = os.getenv("NGROK_DOMAIN", "brook-princess-repeated.ngrok-free.dev")
    ngrok_path = _find_binary("ngrok")

    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    # 1. Prioridad: NGROK con Dominio Fijo Permanente
    if ngrok_path and ngrok_token:
        print("  [NGROK] Conectando túnel con dominio fijo permanente...")
        try:
            # Asegurar authtoken
            subprocess.run(
                [str(ngrok_path), "config", "add-authtoken", ngrok_token],
                capture_output=True,
                creationflags=creation_flags,
            )

            cmd = [
                str(ngrok_path),
                "http",
                "8050",
                f"--url=https://{ngrok_domain}",
                "--log=stdout",
            ]
            _tunnel_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creation_flags,
            )

            public_url = None
            start_time = time.time()
            for line in _tunnel_proc.stdout:
                if "started tunnel" in line or "url=" in line:
                    match = re.search(r"url=(https://[^\s]+)", line)
                    if match:
                        public_url = match.group(1)
                        break
                if time.time() - start_time > 15:
                    break

            if not public_url:
                public_url = f"https://{ngrok_domain}"

            _copy_to_clipboard(public_url)
            print()
            print("=" * 70)
            print("  🚀 GEX DASHBOARD - EN LÍNEA (DOMINIO FIJO PERMANENTE NGROK)")
            print("=" * 70)
            print(f"  🌐 Enlace permanente : {public_url}")
            print("  📋 [OK] ¡Enlace copiado automáticamente a tu portapapeles!")
            print("  💻 Acceso local       : http://127.0.0.1:8050")
            print("=" * 70)
            print("  * ¡Este enlace NUNCA cambia! Puedes guardarlo en favoritos o en tu cel.")
            print("  * Para cerrar la sesión y apagar el enlace, cierra esta ventana.")
            print("=" * 70)
            print()
            webbrowser.open(public_url)
            return
        except Exception as e:
            print(f"  [AVISO NGROK] {e}. Probando Cloudflare...")

    # 2. Fallback: Cloudflare Quick Tunnel
    cf_path = _find_binary("cloudflared")
    if cf_path:
        print("  [CLOUDFLARE] Conectando túnel Cloudflare...")
        try:
            _tunnel_proc = subprocess.Popen(
                [str(cf_path), "tunnel", "--url", "http://127.0.0.1:8050"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creation_flags,
            )

            public_url = None
            start_time = time.time()
            for line in _tunnel_proc.stdout:
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
                webbrowser.open(public_url)
                return
        except Exception as e:
            print(f"  [ERROR Cloudflare] {e}.")

    # 3. Fallback Local
    print("  Acceso web local: http://127.0.0.1:8050")
    webbrowser.open("http://127.0.0.1:8050")


if __name__ == "__main__":
    print("=" * 70)
    print("  GEX DASHBOARD - INICIANDO SISTEMA INSTITUCIONAL")
    print("=" * 70)
    print("  Servidor local: http://127.0.0.1:8050")
    print("  Iniciando túnel en segundo plano...")
    print("=" * 70)

    threading.Thread(target=start_tunnel_and_browser, daemon=True).start()

    try:
        main(host="127.0.0.1", port=8050)
    finally:
        _kill_tunnel()
