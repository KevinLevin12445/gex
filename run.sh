#!/bin/bash
# Linux: ./run.sh desde un terminal, o "Ejecutar en un terminal" con
# clic derecho según el explorador de archivos. En macOS, preferir
# run.command (doble clic directo en Finder).
cd "$(dirname "$0")"
.venv/bin/python run.py
read -p "El programa se ha detenido. Presiona Enter para cerrar..."
