"""Punto de entrada del dashboard, expuesto como comando ``gex-dashboard``.

Inicia la ingesta programada y luego sirve el dashboard Dash en
http://127.0.0.1:8050. Utilizable de tres formas equivalentes:

    gex-dashboard            (tras `pip install .`)
    python -m gex.run
    python run.py            (acceso directo en la raíz del repositorio)
"""
from __future__ import annotations

from dotenv import load_dotenv

import os

from gex.app import create_app
from gex.flowtape import TAPE
from gex.logsetup import setup_logging
from gex.rtquote import PUBLIC_QUOTES, QUOTES
from gex.scheduler import start_scheduler
from gex.tickcapture import CAPTURE


def main(host: str | None = None, port: int | None = None) -> None:
    # carga automáticamente variables de entorno desde .env si existe
    load_dotenv()
    if host is None:
        host = os.getenv("HOST", "0.0.0.0" if os.getenv("PORT") else "127.0.0.1")
    if port is None:
        port = int(os.getenv("PORT", "8050"))
    # consola + logs/gex.log (rotativo): el registro persiste tras cerrar el terminal
    setup_logging()
    start_scheduler()
    # spot en tiempo real: sin credenciales de broker, la llamada no tiene efecto
    QUOTES.start()
    # alternativa gratuita diferida NQ/ES: solo inicia si QUOTES no está corriendo
    PUBLIC_QUOTES.start()
    # order flow firmado sobre opciones: sin credenciales, no tiene efecto
    TAPE.start()
    # captura tick a tick continua NQ/ES (24/5): sesión dxLink dedicada
    CAPTURE.start()
    create_app().run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
