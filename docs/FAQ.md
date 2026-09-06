# FAQ — Preguntas Frecuentes

*[Version française](FAQ.fr.md)* · *[English version](FAQ.en.md)*

Todo lo que necesitas saber para entender los datos mostrados y ejecutar
tu propia instancia.

---

## Los Datos

### ¿De dónde vienen los datos?

Del endpoint público **delayed de CBOE**, el operador de los mercados de opciones
estadounidenses. Es la fuente oficial de las cadenas SPX y NDX: precios bid/ask,
volatilidad implícita, open interest y volumen, para cada strike y cada
vencimiento.

**Sin cuenta, sin clave, sin suscripción.** El dashboard consulta
directamente el endpoint público, gratuitamente.

### ¿Por qué un retraso de 15 minutos?

Es el retraso de la fuente gratuita y pública de CBOE. *Redistribuir* datos en
tiempo real exigiría una licencia profesional costosa — pero para uso
personal, una cuenta de broker es suficiente (ver
[Tiempo real vía cuenta de broker](#tiempo-real-vía-cuenta-de-broker-gratuito-con-la-cuenta)).

**En la práctica, importa mucho menos de lo que se imagina**: la métrica
central de toda la herramienta — el open interest — solo se publica **una vez por
día**, por la mañana, por la OCC. Los muros de gamma, el Gamma Flip y los niveles
clave se basan en él y por tanto se mueven muy poco durante la sesión. El retraso solo afecta
realmente al precio spot de referencia y al flujo intradía.

### ¿Con qué frecuencia se actualizan los datos?

El feed CBOE se regenera aproximadamente cada **60 segundos**, y el dashboard
lo consulta al mismo ritmo durante las horas de mercado (9h30–16h15 hora de
Nueva York). Fuera de ese horario, se pone en espera y muestra el último estado conocido.

### ¿Por qué la pestaña «Posicionamiento» suele estar vacía?

Porque compara el open interest de una sesión a otra, y el OI solo se
publica una vez al día. Mientras la publicación de la mañana no haya tenido lugar,
la comparación no tiene nada que mostrar. Esta pestaña se vuelve útil después de
algunos días de recolección.

### ¿Los niveles están en puntos de índice o de futuros?

Ambos, a elección. El selector **Índice / ES** (o NQ) cambia la visualización.

Es importante: la diferencia entre el índice y su futuro no es despreciable
(del orden de +30 puntos en ES, +150 en NQ). Reportar un nivel SPX bruto sobre
un gráfico ES falsearía todo. El basis se recalcula en cada actualización a
partir de la paridad call-put, y sigue automáticamente el roll trimestral.

---

## Ejecutar tu propia instancia

### ¿Por qué no puedo simplemente usar tu dashboard?

Dos razones, y la primera es la más simple: **no lo necesitas**. La
fuente CBOE es gratuita y sin cuenta — tu instancia mostrará exactamente los
mismos datos.

La segunda tiene que ver con la licencia. Si una instancia se enriquece con datos
opcionales (Databento, o un flujo de broker en tiempo real), estos están bajo
licencia de *uso personal, no redistribuible*. Compartirlos equivaldría a
redistribuirlos, lo cual está prohibido y convertiría al operador en la
categoría «profesional», con las tarifas correspondientes.

De ahí el principio: **el código se comparte, los datos no.**

### ¿Cómo instalo?

Se necesita Python 3.11 o más reciente, y Git.

```
git clone https://github.com/KevinLevin12445/gex.git
cd gex
python -m venv .venv
```

Luego, según el sistema:

```
.venv\Scripts\pip install -r requirements.txt      # Windows
.venv/bin/pip install -r requirements.txt          # macOS / Linux
```

### ¿Cómo inicio?

```
.venv\Scripts\python run.py       # Windows
.venv/bin/python run.py           # macOS / Linux
```

O directamente haciendo doble clic en:
`dist\GEX_Dashboard\GEX_Dashboard.exe`

Luego abrir **http://127.0.0.1:8050** en un navegador.

No se necesita configuración: el dashboard comienza a recolectar
inmediatamente. La interfaz está en español, francés o inglés, detectada desde el
idioma del navegador y modificable con el selector ES/FR/EN.

### ¿Debo dejarlo funcionando permanentemente?

No — pero con un matiz.

Los **niveles** (GEX, muros, Gamma Flip, HVL) son fotos del estado actual:
se reconstruyen íntegramente en la primera actualización, sin importar el
tiempo de inactividad. Nada que recuperar.

El **flujo delta intradía**, en cambio, se mide entre dos muestreos sucesivos: solo puede
captarse si el programa está corriendo durante la sesión. Lo mismo para
el historial de niveles, que se acumula con el tiempo.

En la práctica: inícialo antes de la apertura del mercado US los días que
trabajes. Fuera de sesión, se pone en espera y no consume nada.

### ¿Mis datos se quedan en mi máquina?

Sí, completamente. Todo se almacena localmente en la carpeta `data/` (formato
Parquet). Nada se envía a ningún lado — el dashboard solo escucha en
`127.0.0.1`, es decir, tu propia máquina.

---

## Compartir el veredicto — el bot de Discord

### ¿Puedo compartir mis análisis con amigos sin darles acceso a los datos?

Sí, es exactamente el rol del **bot de Discord** incluido en `discord_bot/`. Transmite
en un canal el **veredicto** del estado del gamma — la conclusión, no el
dato. Tus amigos ven «Gamma negativo en el Nasdaq, contrarian arriesgado»
**sin cuenta de broker ni acceso a las cadenas de opciones**.

Técnicamente, el bot solo consulta la API local del dashboard
(`/api/v1/digest`), que solo devuelve **análisis derivados**: signos,
veredicto, color, y gráficos agregados. Nunca el flujo bruto por contrato.
Es lo que hace que compartir sea compatible con un flujo bajo licencia personal —
compartes una conclusión que *tú* produces, no una redistribución.

### ¿Cómo decide el bot el color del veredicto?

No cuenta los símbolos por igual. SPX, SPY y ES son tres vistas del mismo
S&P 500; NDX, QQQ y NQ del mismo Nasdaq — contarlos por separado equivaldría a
contar tres veces el mismo subyacente. El veredicto razona por **familia
independiente**:

- Cada familia (**S&P**: SPX/SPY/ES — **Nasdaq**: NDX/QQQ/NQ) agrega
  la intensidad de sus símbolos con pesos: **índice cash > ETF > futuro**.
  Un futuro negativo no revierte la señal del índice cash.
- El índice cash (SPX, NDX) es el **índice principal**: si pasa a *fuerte*
  gamma negativo, toda su familia lo es.
- Color: 🔴 **rojo** si las 2 familias son negativas o una en fuerte
  negativo · 🟠 **naranja** si 1 familia negativa o VIX por encima del umbral ·
  🟢 **verde** en caso contrario.

El digest también muestra una **confianza** (alta / media / baja) según la
cobertura de los datos — un veredicto apoyado en los 3 símbolos concordantes de una
familia vale más que un veredicto sobre uno solo.

### ¿Qué comandos entiende el bot?

`!help` (la lista), `!estado`/`!gamma` (el digest completo), `!gamma NQ` (los
valores calculados de un símbolo), `!niveles NQ` (los niveles GEX en texto, con
transposición de escala: `!niveles NDX NQ` muestra los niveles NDX en precios NQ), y
cualquier gráfico como imagen (`!heatmap NQ`, `!delta SPX`, `!vanna SPX`…).
También publica solo a horas fijas y en cada cambio de régimen durante la
sesión, manteniéndose silencioso los fines de semana. Configuración:
[`discord_bot/README.md`](discord_bot/README.md).

---

## Entender los Indicadores

### GEX (Gamma Exposure)

Estimación del gamma que los creadores de mercado deben cubrir, expresada en
**dólares por movimiento de 1 %** del índice. Calculada strike por strike a
partir del open interest y del gamma Black-Scholes.

- **GEX neto positivo** → régimen *estabilizador*. Los creadores de mercado venden
  en la subida y compran en la bajada: la volatilidad se amortigua.
- **GEX neto negativo** → régimen *desestabilizador*. Hacen lo contrario, lo que
  amplifica los movimientos.

### Gamma Flip (o Zero Gamma)

El nivel de precio donde el GEX neto **cambia de signo** — la frontera entre los
dos regímenes anteriores. Es la métrica más seguida de todo el análisis
gamma.

No se lee simplemente del gráfico: el perfil completo se recalcula
sobre una grilla de precios hipotéticos (visible en la pestaña **Gamma Profile**),
luego el cruce se interpola.

### HVL (High Volatility Level)

Mismo cálculo que el Gamma Flip, pero ponderado por el **volumen del día** en lugar
del open interest. Donde el Flip describe la estructura heredada, el HVL
refleja lo que se negocia — y por tanto se cubre — hoy.

Una diferencia marcada entre ambos es en sí misma una información sobre la orientación del
flujo de la sesión.

### Call Wall y Put Support

Las concentraciones de gamma más fuertes, **restringidas direccionalmente**:

- **Call Wall**: el muro de calls más grande **por encima** del precio — resistencia.
- **Put Support**: el muro de puts más grande **por debajo** — soporte.

Esta restricción no es cosmética. El muro de puts más grande en valor
absoluto puede estar por encima del precio, en cuyo caso llamarlo
«soporte» no tendría sentido.

### 1D Min y 1D Max

Los límites del movimiento esperado en el vencimiento más cercano, deducidos del precio
del **straddle at-the-money**. El straddle *es* la estimación de movimiento del
mercado mismo — ninguna hipótesis de modelo interviene.

### GEX1 a GEX5

Los cinco strikes con el gamma más importante en valor absoluto, sin restricción
de dirección. Son los muros brutos, clasificados por peso. La casilla **Solo Major Walls**
filtra los que pesan menos del 25 % del más fuerte.

### DEX (Delta Exposure)

El equivalente del GEX para el delta: la exposición direccional que los creadores
de mercado mantienen en cada strike.

### Vanna y Charm (pestaña dedicada)

Las griegas de segundo orden, que explican flujos de cobertura que el
gamma solo no captura:

- **Vanna** — sensibilidad del delta a la volatilidad implícita. Cuando la IV se
  relaja, los creadores de mercado deben recomprar delta: es la mecánica
  de las subidas lentas sin catalizador aparente.
- **Charm** — decrecimiento del delta con el **paso del tiempo**. Este flujo es
  puramente mecánico y por tanto predecible; explica una parte de las derivas de
  fin de sesión y de los comportamientos de semana de vencimiento.

### El flujo delta

Una estimación del delta intercambiado, minuto por minuto, obtenida multiplicando la
variación de volumen de cada contrato por su delta.

**Su limitación debe entenderse**: este feed no dice si una transacción fue
iniciada como compra o como venta. Es por tanto una medida de *presión ponderada
por el delta*, no un verdadero flujo de órdenes firmado. Indica la intensidad
y la concentración, no la dirección agresiva.

---

## Opciones Avanzadas (opcionales, de pago)

El dashboard funciona íntegramente sin nada de lo que sigue.

### Historial vía Databento

Permite pre-rellenar varios meses de historial diario (GEX neto, Gamma
Flip) y recuperar el flujo intradía de sesiones pasadas.

Facturación por dato descargado. El script muestra **un presupuesto antes de cualquier
descarga** y se niega a superar un tope que tú fijas
(`--max-cost`). Los archivos brutos se conservan localmente: relanzar nunca
refactura lo que ya fue recuperado.

Requiere una cuenta Databento y la variable de entorno
`DATABENTO_API_KEY` (ver `.env.example`).

A tener en cuenta: los datos de la sesión más reciente permanecen bajo licencia
«tiempo real» durante aproximadamente un día hábil. Un error de licencia sobre la
víspera es normal — basta con esperar.

### Tiempo real vía cuenta de broker (gratuito con la cuenta)

Una cuenta de broker que dé acceso a dxFeed — el dashboard está escrito para
tastytrade, que incluye estos datos sin cargo — pasa a directo:

- el **spot** de los subyacentes y de los futuros;
- el **GEX neto recalculado a ese spot**, por tanto la distancia al Gamma Flip y la
  lectura del régimen, que se vencen en pocos minutos;
- el registro de **velas al minuto**, y la recuperación de varias
  semanas de **historial** de una sola vez.

**Las cadenas de opciones siguen retrasadas**: continúan viniendo de CBOE.
Los muros de gamma y el Gamma Flip no se mueven más por ello,
ya que se basan en el open interest publicado una vez al día.

Configuración: crear una aplicación OAuth desde la configuración de la cuenta,
ejecutar `python -m gex.tt_auth` para obtener un token, luego configurar
`TASTYTRADE_CLIENT_ID`, `TASTYTRADE_CLIENT_SECRET` y `TT_REFRESH` como variables
de entorno — nunca en un archivo del repositorio. Sin estas variables, el
módulo permanece inactivo y nada cambia.

Abrir una cuenta de broker es una gestión personal y comprometedora; el
dashboard funciona perfectamente sin ella, y esto no es una recomendación.

**Estos datos nunca son redistribuibles**: permanecen en la instancia
local de su titular. El programa aplica la regla por construcción —
procedencia marcada al escribir, y exportación limitada solo a datos CBOE.

---

## Limitaciones Conocidas

- **Retraso de 15 minutos** en la fuente gratuita. Herramienta de lectura de
  estructura, nunca de ejecución.
- **El open interest es diario.** Ningún proveedor, gratuito o de pago, cambia
  eso: es la OCC quien lo publica.
- **El lado de las transacciones no es observable** en el flujo gratuito (ver
  la sección sobre el flujo delta).
- **Hipótesis de posicionamiento de los creadores de mercado.** Como todas las herramientas
  de este tipo, el cálculo supone que los dealers están largos de calls y cortos
  de puts. Es una convención extendida y útil, no una verdad medida.
- **El endpoint CBOE no es contractual**: su formato puede cambiar sin
  previo aviso. La ingesta está aislada para poder conectar otra fuente.

---

## Aviso Legal

Esta herramienta sirve **exclusivamente para el análisis**. No envía ninguna orden, no se
conecta a ninguna cuenta de trading, y no constituye ni asesoramiento de
inversión ni una recomendación. Los cálculos se basan en convenciones
públicas e hipótesis explicadas arriba, susceptibles de ser incorrectas.

Distribuido bajo [licencia MIT](LICENSE), sin ninguna garantía.
