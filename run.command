#!/bin/bash
# Doble clic en Finder (macOS): inicia el dashboard. El sufijo
# .command es lo que hace que macOS lo ejecute en lugar de abrirlo
# en un editor de texto.
cd "$(dirname "$0")"
.venv/bin/python run.py
read -p "El programa se ha detenido. Presiona Enter para cerrar..."
