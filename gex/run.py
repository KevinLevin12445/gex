"""Punto de entrada del dashboard, expuesto como comando ``gex-dashboard``.

Inicia la ingesta programada y luego sirve el dashboard Dash en
http://127.0.0.1:8050. Utilizable de tres formas equivalentes:

    gex-dashboard            (tras `pip install .`)
    python -m gex.run
    python run.py            (acceso directo en la raíz del repositorio)
"""
from __future__ import annotations

from dotenv import load_dotenv

from gex.app import create_app
from gex.flowtape import TAPE
from gex.logsetup import setup_logging
from gex.rtquote import PUBLIC_QUOTES, QUOTES
from gex.scheduler import start_scheduler
from gex.tickcapture import CAPTURE


def main(host: str = "127.0.0.1", port: int = 8050) -> None:
    # carga automáticamente variables de entorno desde .env si existe
    load_dotenv()
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
    create_app().run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
