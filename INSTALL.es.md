# Guía de instalación paso a paso

*[Versión en francés](INSTALL.md) · [English version](INSTALL.en.md)*

Esta guía está diseñada para cualquier persona que **nunca haya instalado este tipo de programa**. No se requieren conocimientos previos. Lleva unos 10-15 minutos.

Al finalizar, tendrás el dashboard funcionando en tu navegador. **Sin cuentas, sin claves y sin pagos**: los datos provienen de una fuente pública gratuita.

---

## Paso 1 — Instalar Python

Python es el lenguaje en el que está escrito el programa.

### En Windows
1. Ve a **https://www.python.org/downloads/**
2. Haz clic en el botón amarillo **«Download Python 3.x»**.
3. Abre el archivo descargado.
4. **⚠️ PASO CRÍTICO**: En la primera pantalla del instalador, marca la casilla **«Add python.exe to PATH»** en la parte inferior antes de hacer clic en *Install Now*.
5. Haz clic en **Install Now** y finaliza la instalación.

---

## Paso 2 — Descargar el programa

Descarga el ZIP desde GitHub o clona el repositorio con Git:
```bash
git clone https://github.com/Darthreign/gex-dashboard.git
```

---

## Paso 3 — Abrir el terminal en la carpeta

En Windows, abre la carpeta del proyecto, haz clic en la barra de direcciones superior, escribe `powershell` y presiona **Enter**.

---

## Paso 4 — Instalar y ejecutar

Ejecuta los siguientes comandos uno a uno:

### En Windows:
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run.py
```

O simplemente ejecuta haciendo doble clic en **`run.bat`**.

---

## Paso 5 — Abrir el dashboard

Abre tu navegador y entra en: **`http://127.0.0.1:8050`**

¡Listo! 🎉
