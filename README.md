# GEX Dashboard — Análisis de Gamma & Delta Exposure

[Licencia MIT](LICENSE) — Herramienta de **análisis institucional**: sin trading, sin ejecución, sin asesoramiento de inversión. Obtiene datos desde los endpoints públicos de CBOE o en tiempo real mediante cuenta de broker (dxFeed / tastytrade).

> ⚠️ **Aviso de Riesgo:** El trading de opciones y derivados conlleva un alto riesgo de pérdida. Esta herramienta se proporciona exclusivamente con fines educativos y de investigación cuantitativa.

---

## ⚡ Cómo Ejecutar el Proyecto

Tienes tres formas inmediatas de ejecutar el dashboard:

### Opción 1: Ejecución Directa en 1 Clic (Recomendada en Windows)
Haz doble clic en el archivo:
```bat
run.bat
```
Esto iniciará el servidor local y podrás acceder en tu navegador a: **`http://127.0.0.1:8050`**

### Opción 2: Ejecutable Compilado Independiente
Puedes ejecutar directamente la aplicación sin necesidad de consola de comandos:
```
dist\GEX_Dashboard\GEX_Dashboard.exe
```

### Opción 3: Vía Consola Python
```bash
# Activar entorno virtual
.\.venv\Scripts\activate

# Instalar dependencias (si es la primera vez)
pip install -r requirements.txt

# Iniciar servidor
python run.py
```

Para recompilar el ejecutable tras realizar modificaciones, ejecuta:
```bat
build_exe.bat
```

---

## 🚀 Funcionalidades Principales

- **Heatmap de Absorción y Liquidez Institucional (Estilo AlgoAlpha)**:
  - Mapa de calor de liquidez continuo con interpolación cúbica e intensidad de órdenes.
  - Perfil de Volumen lateral con identificación automática del **POC (Point of Control)**, Value Area High (VAH) y Value Area Low (VAL).
  - Perfil de Delta lateral con desbalance de agresividad compradora vs vendedora.
  - Subplots sincronizados en tiempo real y selector dinámico de rangos de strikes.
- **Estructura GEX & DEX por Strike**:
  - Niveles clave intradía: Muros de Gamma (**GEX1–5**), **Flip** (Zero Gamma) y **HVL** (High Volatility Level).
  - Descomposición Call/Put interactiva con visualización de skew de volatilidad implícita (IV).
- **Gamma Profile Multivencimiento**:
  - Simulación de sensibilidad de dealers según desplazamientos del precio spot (-8% a +8%).
  - Filtro por plazos: 0DTE, Semanal, Mensual y Global.
- **Griegas de Segundo Orden (Vanna & Charm)**:
  - Impacto del paso del tiempo y caídas de volatilidad en los flujos de cobertura de creadores de mercado.
- **Posicionamiento y Open Interest**:
  - Comparativa de variación neta de contratos entre sesiones consecutivas.
- **Ajuste CFD Automático & Exportación TradingView**:
  - Transposición de niveles a contratos CFD de cualquier broker (US100, US500, XAUUSD, BTCUSD).
  - Generación de código Pine Script v5 en 1 clic para ver los niveles en TradingView.

---

## 📊 Fuentes de Datos

| Característica | CBOE (Pública / Gratuita) | dxFeed / tastytrade (Tiempo Real) |
|---|---|---|
| **Requisitos** | Ninguno (funciona de inmediato) | Cuenta de broker configurada en `.env` |
| **Latencia** | Retraso estándar ~15 min | Tiempo real tick a tick |
| **Activos soportados** | SPX, NDX, SPY, QQQ, GC, BTC | Cadenas nativas índice y futuros (ES, NQ, etc.) |
| **Order Flow Firmado** | Proxy de volumen | Flujo institucional firmado con lado agresor |

---

## 📁 Estructura del Proyecto

```
gex2-main/
├── data/              # Datos de mercado persistidos en formato Parquet
├── dist/              # Ejecutable compilado para Windows (GEX_Dashboard.exe)
├── gex/               # Código fuente principal de la aplicación
│   ├── assets/        # Estilos CSS de alta fidelidad, JavaScript y modales
│   ├── app.py         # Interfaz y servidor Dash (gráficos, callbacks y heatmap)
│   ├── metrics.py     # Cálculo de GEX, DEX, Zero Gamma y niveles institucionales
│   ├── greeks.py      # Modelo Black-Scholes vectorizado
│   ├── scales.py      # Transposición de escalas y ajuste CFD
│   ├── rtquote.py     # Cotizaciones en tiempo real y velas
│   ├── flowtape.py    # Procesamiento de flujo y order flow
│   ├── store.py       # Almacenamiento optimizado en Parquet
│   └── run.py         # Punto de arranque del servidor
├── .env               # Credenciales y configuración local
├── .env.example       # Plantilla de variables de entorno
├── build_exe.bat      # Script para compilar la aplicación a .exe
├── GEX_Dashboard.spec # Archivo de configuración para PyInstaller
├── launcher.py        # Lanzador para el ejecutable con apertura de navegador
├── LICENSE            # Licencia del proyecto
├── pyproject.toml     # Especificación del paquete Python
├── requirements.txt   # Dependencias del proyecto
├── run.bat            # Acceso directo para ejecutar en Windows en 1 clic
└── run.py             # Script de entrada para arrancar con python run.py
```
