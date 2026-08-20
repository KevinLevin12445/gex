# GEX Dashboard

Un dashboard profesional, interactivo y de código abierto para analizar la estructura de opciones y el flujo institucional de **SPX**, **NDX**, **SPY**, **QQQ**, **ES** y **NQ** — muros de gamma, Gamma Flip, HVL, Order Flow firmado en tiempo real, CVD de Gamma y perfil de volatilidad.

---

## 🚀 Conexión de Datos y APIs

El dashboard puede funcionar de forma **100% gratuita sin APIs** (utilizando el feed público de CBOE) o conectarse a feeds institucionales en tiempo real (**dxFeed**, **Tastytrade**, **Databento**).

### Configuración del archivo `.env`:

1. Crea un archivo llamado `.env` en la raíz del proyecto (puedes basarte en `.env.example`).
2. Pega tus credenciales según tu proveedor:

```env
# ==============================================================================
# CONFIGURACIÓN DE APIS Y FEEDS EN TIEMPO REAL
# ==============================================================================

# 1. API DIRECTA DE DXFEED (Opciones OPRA, Futuros CME, Order Flow TimeAndSale)
# Obtén tu token en https://dxfeed.com
DXFEED_AUTH_TOKEN="tu_token_de_dxfeed"
DXFEED_ENDPOINT="wss://live.dxfeed.com/live/websocket"

# 2. TASTYTRADE / DXLINK (Si usas cuenta de broker Tastytrade)
TT_REFRESH="tu_refresh_token"
TASTYTRADE_CLIENT_ID="tu_client_id"
TASTYTRADE_CLIENT_SECRET="tu_client_secret"

# 3. DATABENTO (Opcional, para descargas históricas de alta resolución)
# Obtén tu clave en https://databento.com
DATABENTO_API_KEY="db-tu_clave_databento"
```

---

## 📊 Características Principales

- **Order Flow Signé Cumulé (Tiempo Real)**: Mide quién agrede el libro de órdenes (Bid vs Ask) con doble eje: Delta Neto ponderado en $\$M$ y contratos de Calls/Puts.
- **Gamma Échangé Cumulé (CVD de Gamma)**: Acumulación de gamma con desacople entre Calls $(\gamma+)$ y Puts $(\gamma-)$ para identificar saturación de cobertura corta.
- **Spot vs Gamma Flip**: Superposición del precio Spot en tiempo real y el nivel de Gamma Flip para detección inmediata de cambios de régimen de volatilidad $(\gamma+ \leftrightarrow \gamma-)$.
- **Gamma Exposure (GEX) y Delta Exposure (DEX)** por strike y por vencimiento (0DTE, Semanal, Mensual).
- **Niveles clave institucionales**: Gamma Flip, High Volatility Level (HVL), Call Wall, Put Support, 1D Min / 1D Max.
- **Heatmap interactivo** con velas de precios y perfil de gamma superpuesto.
- **Vanna & Charm**, Skew de volatilidad implícita y variación de Open Interest.
- **Transposición de escalas**: Conversión instantánea entre índices de contado y futuros CME (SPX $\leftrightarrow$ ES, NDX $\leftrightarrow$ NQ).
- **Exportación a TradingView con 1 Clic**: Generación automática de script PineScript.

---

## 🛠️ Instalación Rápida

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/KevinLevin12445/gexES.git
   cd gexES
   ```

2. **Crear entorno virtual e instalar dependencias**:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\pip install -r requirements.txt      # En Windows
   # .venv/bin/pip install -r requirements.txt        # En macOS / Linux
   ```

3. **Configurar tu API (Opcional)**:
   Crea tu archivo `.env` en la raíz con tus claves de dxFeed o Tastytrade.

4. **Iniciar el servidor**:
   - En Windows:
     ```bash
     .\.venv\Scripts\python run.py
     ```
   - O doble clic en `run.bat`.

5. **Abrir en el navegador**:
   Entra a **[http://127.0.0.1:8050](http://127.0.0.1:8050)**.

---

## 📄 Licencia

Distribuido bajo licencia MIT. Esta herramienta es para fines analíticos e informativos únicamente.
