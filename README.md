# GEX Dashboard — Análisis de Gamma/Delta Exposure (SPX, NDX, SPY, QQQ, GC, BTC)

*[English version](README.en.md)* · *[Version française](README.fr.md)* · *[FAQ](FAQ.md)* · *[Aviso Legal](DISCLAIMER.md)*

[Licencia MIT](LICENSE) — herramienta de **análisis únicamente**: sin trading,
sin ejecución, sin asesoramiento de inversión. Cada instancia obtiene sus
propios datos desde el endpoint público delayed de CBOE; este proyecto no
redistribuye ningún dato de mercado.

> ⚠️ **El trading de opciones y derivados conlleva un alto riesgo de pérdida.**
> Esta herramienta se proporciona con fines educativos, sin garantía, y no
> constituye asesoramiento de inversión. Lea el [aviso legal completo](DISCLAIMER.md)
> antes de utilizarla.

## Vista General

| Vista principal | Gamma Profile |
|---|---|
| ![Vista principal](docs/screenshots/01-vue-principale.png) | ![Gamma Profile](docs/screenshots/02-gamma-profile.png) |
| GEX/DEX por strike, niveles 0DTE, flujo delta, historial | Perfil de GEX neto según el spot, descompuesto por vencimiento |

| Vanna & Charm | Posicionamiento |
|---|---|
| ![Vanna y Charm](docs/screenshots/03-vanna-charm.png) | ![Posicionamiento](docs/screenshots/04-positionnement.png) |
| Griegas de segundo orden por strike | Variación de open interest entre sesiones |

Dashboard de **análisis únicamente** (sin trading) que reconstruye las métricas
de estructura de mercado al estilo SpotGamma a partir de las cadenas de opciones CBOE:
Gamma Exposure por strike, Delta Exposure, GEX neto, nivel Zero Gamma,
ratios put/call, skew IV, y proxy de flujo delta intradía.

**¿Quieres entender qué muestra cada pestaña y cada cifra?** →
[Guía ilustrada](docs/guide/README.md), un archivo por pestaña más un archivo
que explica cada número, pensado para alguien que descubre el dashboard
sin conocer nada sobre opciones.

## Fuentes de Datos

El dashboard aplica **una regla única, en todas partes**: la fuente en tiempo real si
está disponible, la fuente gratuita en caso contrario.

| | CBOE (público) | dxFeed (cuenta de broker) |
|---|---|---|
| Cuenta requerida | no | sí (gratuita con la cuenta) |
| Frescura | **~15 min de retraso** | tiempo real |
| Lado comprador/vendedor | no observable | **proporcionado por la fuente** |
| Redistribuible | sí | **no** — uso estrictamente personal |

**Sin cuenta de broker, no falta nada esencial**: todos los niveles, todos
los regímenes y todos los gráficos funcionan con la fuente pública. Solo
el order flow firmado y las velas de minuto en futuros requieren una cuenta.

### CBOE — fuente por defecto

Endpoint público delayed (no documentado oficialmente):
`https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` (índices
con prefijo `_`). Un GET devuelve la cadena completa — bid/ask, IV, open interest,
volumen, Greeks — más el spot. **Retraso ~15 min en la fuente**, regenerado ~cada
60 s (timestamp del feed en UTC). Subyacentes seguidos: SPX, NDX, SPY,
QQQ, GC (Oro) y BTC (Bitcoin) (`gex/config.py`).

### dxFeed — cuando una cuenta de broker está configurada

Lo que el tiempo real cambia, medido en lugar de supuesto: sobre los mismos strikes
0DTE, dxFeed veía **3 a 6 veces más volumen** que CBOE en el mismo instante,
para un open interest **idéntico al contrato**. No es una fuente más
aproximada, es la misma sin el retraso.

- **Cadenas nativas** SPX / NDX / SPY / QQQ (`gex/idxopt.py`) y NQ / ES / GC / BTC
  (`gex/futopt.py`) — las opciones sobre futuros tienen su propia estructura de
  gamma, distinta del índice transpuesto.
- **Order flow firmado** (`gex/flowtape.py`): cada transacción lleva su lado
  agresor, proporcionado por la fuente. Ninguna heurística de clasificación.
- **Spot en tiempo real** y velas de 1 min para el Heatmap.

⚠️ Estos datos nunca salen de la máquina: `gex/export.py` solo autoriza la
exportación de las líneas con `source == "cboe"`.

## Instalación

**¿Principiante, nunca has instalado este tipo de herramienta?** → sigue la
**[guía paso a paso ilustrada](INSTALL.md)** (15 min, sin conocimientos
previos necesarios, sin líneas de comando que entender).

De lo contrario, la [instalación asistida por Claude Code](#instalación-asistida-claude-code)
o el [inicio manual](#inicio) más abajo.

## Instalación Asistida (Claude Code)

Si usas [Claude Code](https://claude.com/claude-code), ábrelo en una
carpeta vacía y pega este prompt — lo hace todo, incluyendo el registro del
servidor MCP:

```
Instala el dashboard GEX (análisis de opciones SPX/NDX) en mi máquina.

Repositorio: https://github.com/KevinLevin12445/gex

Pasos:
1. Verifica que Python 3.11+ y git estén disponibles. Si falta alguno,
   explícame cómo instalarlo y detente ahí.
2. Clona el repositorio en la carpeta actual y posiciónate en ella.
3. Crea un entorno virtual .venv e instala requirements.txt.
4. Ejecuta la suite de tests (pytest tests/ -q) para validar la instalación:
   todos los tests deben pasar.
5. Adapta .mcp.json a mi sistema: reemplaza el valor de "command" por la
   ruta ABSOLUTA al python del venv (Windows: .venv\Scripts\python.exe,
   macOS/Linux: .venv/bin/python). El archivo incluido contiene una ruta
   Windows relativa que no funciona en otros sistemas.
6. Inicia el dashboard (python run.py) y dame la URL para abrir.
7. Explícame que debo reiniciar Claude Code desde esta carpeta para
   activar el servidor MCP "gex-data", y lista las herramientas que expone.

Importante: no se necesita ninguna cuenta, clave API ni suscripción — los
datos provienen del endpoint público gratuito de CBOE. No me pidas ninguna
credencial. Los módulos backfill.py (Databento) y tt_auth.py (tastytrade)
son opcionales y de pago: ignóralos completamente.
```

El servidor MCP permite luego consultar tus datos en lenguaje natural
(«analiza la estructura gamma actual», «¿dónde están los muros en NDX?»).

## Inicio

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run.py        # dashboard en http://127.0.0.1:8050
```

O simplemente ejecuta el archivo compilado incluido:
`dist\GEX_Dashboard\GEX_Dashboard.exe`

Tests: `.venv\Scripts\python -m pytest tests/`

### Instalación como paquete (opcional)

El proyecto es un paquete Python estándar. Instalado, expone dos comandos,
sin necesidad de estar en la carpeta de fuentes:

```
pip install .                      # o: pip install -e .  (modo desarrollo)
gex-dashboard                      # inicia el dashboard
gex-mcp                            # inicia el servidor MCP
```

Una vez instalado así, `data/` y `logs/` se crean **en la carpeta
actual** (y no en las fuentes): ejecuta el comando desde la carpeta donde
quieras conservar tu historial.

## Servidor MCP — consultar tus datos en lenguaje natural

Es lo que realmente distingue esta herramienta de un dashboard clásico: una vez
activo el servidor MCP, puedes hacer tus preguntas directamente a Claude, que
lee tus archivos Parquet y te responde sobre **tus** datos.

```
«¿Dónde están los muros de gamma en NDX?»
«Analiza el régimen gamma actual en SPX»
«¿Cómo ha evolucionado el GEX neto esta semana?»
«Muéstrame el flujo delta de la última sesión»
```

⚠️ **El servidor MCP solo se activa al iniciar Claude Code, desde la
carpeta del proyecto.** Si acabas de instalar la herramienta, cierra Claude Code y
vuélvelo a abrir desde esta carpeta — de lo contrario los comandos permanecerán invisibles.
Es el único paso que puede confundir en la instalación.

El archivo [`.mcp.json`](.mcp.json) registra el servidor automáticamente.
Contiene una ruta **Windows relativa**: en macOS o Linux, reemplaza el
valor de `command` por la ruta absoluta a `.venv/bin/python`, de lo
contrario el servidor fallará sin mensaje explícito.

Herramientas expuestas: `get_market_context` (síntesis: régimen, muros más
cercanos al spot, VIX), `get_gex_summary`, `get_gex_by_strike` (muros de gamma),
`get_flow_delta`, `get_history`, `get_reports`, `get_log_tail`.

Estas herramientas siguen la misma regla de fuente que la interfaz: responden con
la cadena nativa cuando existe, con CBOE si no — para evitar dos verdades
diferentes según se mire la pantalla o se consulte a Claude.

## Bot Discord — compartir el veredicto (opcional)

Un componente separado y ligero ([`discord_bot/`](discord_bot/README.md)) transmite
en un canal de Discord el **veredicto** del estado del gamma. Tus amigos ven tu
conclusión («Gamma negativo en el Nasdaq, contrarian arriesgado») **sin cuenta
de broker ni acceso a los datos brutos**: el bot solo consulta la API local del
dashboard (`/api/v1/digest`), que solo devuelve análisis derivados — nunca
las cadenas de opciones.

- **Posts automáticos** a horas fijas (8h30 / 15h25 / 15h35 / 17h30 París) y
  en cada **cambio de régimen** durante la sesión US. Silencioso los fines de semana.
- **Veredicto por familia**: el régimen se juzga por clase de activo independiente
  — **S&P** (SPX/SPY/ES), **Nasdaq** (NDX/QQQ/NQ), **Commodities** (GC) y **Crypto** (BTC) — con un peso mayor al índice cash que al ETF y luego al futuro.
  Color: 🔴 2 familias negativas o una en fuerte negativo · 🟠 1 familia
  negativa o VIX elevado · 🟢 en caso contrario. Una línea de **confianza** refleja la
  cobertura de los datos.
- **Comandos bajo demanda**: `!estado`/`!gamma` (digest), `!gamma NQ` (valores
  calculados), `!niveles NQ` (niveles GEX, transponibles: `!niveles NDX NQ`),
  cualquier gráfico como imagen (`!heatmap NQ`, `!delta SPX`…) y `!help`.

El bot solo expone conclusiones calculadas: es lo que permite compartirlas
sin redistribuir un flujo bajo licencia personal. Configuración en el
[README del bot](discord_bot/README.md).

## Funcionalidades

- GEX / DEX por strike (ventana ajustable ±2/4/10 %), calls/puts al pasar el cursor
- Niveles 0DTE trazados: **GEX1-5** (muros de gamma), **Flip** (zero gamma,
  ponderado por open interest), **HVL** (basculamiento ponderado por el volumen del día)
- GEX neto, ratios P/C, skew IV por vencimiento, vista por plazo (0DTE/semanal/mensual)
- Flujo delta 1 min (proxy Δvolumen×δ) con selector de día
- Historial GEX neto & spot vs zero gamma (se acumula automáticamente)
- Backfill histórico opcional vía Databento (`gex/backfill.py`, de pago,
  presupuesto mostrado antes de cualquier descarga)
- **Order flow firmado** en opciones (cuenta de broker): lado agresor proporcionado
  por la fuente, ponderado por el delta — una medida de impacto de cobertura, no
  un recuento de contratos. Piernas de combos aisladas del flujo neto.
- VIX en confluencia, en directo si la suscripción lo permite, retrasado si no
- Servidor MCP (`gex/mcp_server.py`) para consultar los datos desde Claude
- Bot Discord opcional ([`discord_bot/`](discord_bot/README.md)) que difunde el
  veredicto del estado del gamma (solo análisis derivados) — ver arriba
- Títulos de gráficos clicables: cada título enlaza a la sección de la
  [guía ilustrada](docs/guide/README.md) que lo explica
- **Ajuste CFD automático (Yahoo Finance)**: conversión precisa de precios de futuros CME a precios CFD de cualquier broker (US100, US500, XAUUSD, BTCUSD).
- **Exportación a TradingView con 1 clic**: genera automáticamente la cadena de niveles para el indicador Pine Script v5.

## Backfill Databento (opcional)

Copiar `.env.example`, rellenar `DATABENTO_API_KEY`, luego por ejemplo:
`python -m gex.backfill --daily-days 31 --intraday-days 7 --max-cost 40`.
Los archivos brutos se conservan en `data/databento/`: relanzar nunca
refactura lo que ya está descargado. La pasarela Databento puede
devolver 504 en consultas grandes: preferir tramos de una
semana (`--end` + `--daily-days 7`).

## Arquitectura

- `gex/ingest.py` — fetch + parsing de cadenas CBOE (retry/backoff)
- `gex/idxopt.py` — cadenas de índice nativas vía dxFeed (tiempo real)
- `gex/futopt.py` — cadenas de opciones sobre futuros NQ/ES/GC/BTC vía dxFeed
- `gex/flowtape.py` — order flow firmado (TimeAndSale + Greeks)
- `gex/rtquote.py` — spot en tiempo real y velas 1 min
- `gex/greeks.py` — Black-Scholes vectorizado (probado con valores de Hull)
- `gex/metrics.py` — GEX/DEX por strike, zero gamma, P/C, flujo delta
- `gex/store.py` — Parquet: snapshots completos (10 min), flujo (1 min), historial
- `gex/scheduler.py` — bucle APScheduler, horarios de mercado ET (9:30–16:15)
- `gex/app.py` — dashboard Dash (refresco automático 60 s)
- `gex/scales.py` — transposición de escalas índice↔futuros y ajuste CFD

## Convenciones de Cálculo

- **GEX** ($ por 1 % de movimiento) = γ × OI × 100 × spot² × 0.01 — calls positivos,
  puts negativos (convención «naive» SpotGamma: dealers largos calls, cortos puts).
- **Zero Gamma**: recálculo del perfil de GEX neto sobre una grilla de spots ±8 %
  (IV y vencimientos fijos), interpolación del cruce por cero más cercano al spot.
- **Flujo delta** (proxy) = Δvolumen entre dos pulls × δ × 100 × spot. El lado
  taker no es observable en este feed: presión delta-ponderada, no un
  verdadero order-flow firmado.
- Vencimientos fijados a 16:00 ET; contratos expirados excluidos; 0DTE conservado en sesión
  con piso de 5 min sobre t.

## Apoyar el proyecto

El dashboard es gratuito, sin publicidad y sin recolección de datos — y así
seguirá. Si lo usas y te ahorra tiempo, puedes invitar un café al desarrollo:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-dwarfsquirrel-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/dwarfsquirrel)

Es completamente opcional. Una donación no otorga derecho a soporte, prioridad
sobre funcionalidades ni garantía alguna — los términos de la
[licencia MIT](LICENSE) y del [aviso legal](DISCLAIMER.md) permanecen
sin cambios. Reportar un bug o proponer una mejora ayuda igualmente.

## Limitaciones Conocidas

- **Sin cuenta de broker**: datos retrasados 15 min — herramienta de lectura de
  estructura, sin ejecución. Con una cuenta, el retraso desaparece pero la herramienta
  sigue siendo una herramienta de análisis: sin órdenes, sin ejecución, sin asesoramiento.
- El order flow firmado solo cubre strikes a ±1.5 % del spot en los 2
  vencimientos más cercanos (donde se negocia lo esencial). Sus amplitudes no
  son comparables a las del proxy CBOE, que abarca toda la cadena.
- Endpoint CBOE no contractual: el formato puede cambiar (la ingesta está
  aislada para poder conectar otra fuente, ej. Tradier).
- **SPY y QQQ**: estos ETF pagan dividendo, pero el cálculo supone un
  rendimiento nulo (q = 0). La aproximación es pequeña en vencimientos
  cortos pero no es nula — los índices SPX y NDX no tienen este
  sesgo. Además no tienen futuro asociado, por lo que el selector
  Índice/Futuros está inactivo para ellos.
