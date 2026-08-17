---
name: analisis-tecnico-boa
description: "Genera un informe de analisis tecnico bursatil completo como archivo HTML autocontenido e interactivo, con grafico de precio de niveles toggleables, perfil de volumen con POC y value area, indicador Koncorde de acumulacion y distribucion, gauge de score, calculadora de posicion, simulador de escenarios y tooltips explicativos en cada indicador. Usar SIEMPRE que el usuario mencione un ticker o una accion y pida analisis tecnico, chartismo, informe de trading, evaluacion de un activo, punto de entrada, stop loss o take profit, soportes y resistencias, RSI, MACD, ADX o medias moviles, perfil de volumen, volume profile, POC, value area, Koncorde, manos fuertes, dinero institucional, acumulacion o distribucion, y tambien cuando pregunte de manera informal que ve en un papel, como viene cotizando algo, si estan comprando los grandes o si conviene entrar ahora. Aplica igual a acciones, indices, ETFs, CEDEARs, cripto y futuros, incluso si el usuario nunca dice las palabras informe ni HTML."
---

# Informe de análisis técnico interactivo

Esta skill produce un entregable concreto: **un archivo `.html` autocontenido** que el usuario abre en el navegador y puede usar para tomar decisiones. No es un texto largo en el chat.

La razón de que sea HTML y no prosa es que el análisis técnico es intrínsecamente visual y paramétrico. Un soporte en 142,30 no significa nada hasta que se ve dónde cae en el gráfico; un R/R de 2,4 no significa nada hasta que el usuario mete su capital y ve cuánto pierde si salta el stop. Los elementos interactivos existen para que el lector pueda interrogar el análisis, no para decorarlo.

## Flujo de trabajo

1. **Recolectar la serie OHLCV** (ver *Datos*) y guardarla como `serie.json`:
   `{"fechas":["YYYY-MM-DD",...], "ohlc":[[o,h,l,c],...], "volumen":[...]}`
2. **Calcular los indicadores**:
   `python3 scripts/compute_indicators.py serie.json calculado.json`
   Devuelve RSI, MACD, ADX, ATR, estocástico, %B, volumen relativo, las cuatro medias móviles (WMA10, WMA21, EMA50, SMA200) con su bloque de lectura `medias_estado`, el **perfil de volumen** y el **Koncorde**. Corré esto siempre que tengas la serie: son números reproducibles en lugar de estimaciones tuyas.
   La ventana del perfil (`--vp-ventana`, default 120) debería acompañar al horizonte declarado: unas 60 velas para swing de semanas, 120-250 para posición de meses. Un perfil de 250 velas sobre un trade de dos semanas describe un mercado que ya no existe.
   **Pasale toda la historia que hayas conseguido.** El cálculo usa siempre la serie completa y `--velas-grafico` (default 250, `0` = todas) decide solo cuántas se dibujan: el script devuelve en `precio_serie` la cola ya recortada, con las medias calculadas sobre el total. Por eso descargar de más no ensucia el gráfico, y descargar de menos sí rompe la SMA200.
3. **Analizar y puntuar** — el score con la rúbrica de `references/scoring.md`.
4. **Escribir `analisis.json`** siguiendo el contrato de abajo, copiando tal cual los bloques `precio_serie`, `volume_profile` y `koncorde` de `calculado.json` y agregándoles la `lectura` interpretativa donde corresponda. `precio_serie` ya viene armado y recortado, con `fechas`, `ohlc`, `volumen` y `medias` alineados entre sí: **no lo rearmes ni le mezcles velas de otra fuente**, o las medias dejan de corresponderse con el precio. El bloque `medias_estado` **no se copia**: es insumo tuyo para puntuar Tendencia y redactar el indicador de medias con números medidos en lugar de estimados.
5. **Renderizar**: `python3 scripts/build_report.py analisis.json informe_TICKER_YYYYMMDD.html`
6. **Revisar las advertencias** que imprime el script y corregir el JSON si aparecen incoherencias.
7. **Entregar el archivo** y resumir en el chat en 3-5 frases: sesgo, score, niveles clave del plan y qué lo invalida. El detalle vive en el HTML.

No escribas HTML a mano. El template ya resuelve el layout, los SVG, los tooltips y los widgets; tu trabajo es el análisis y el JSON. Si necesitás cambiar algo visual, editá `assets/report_template.html`, no generes un archivo paralelo.

Tampoco calcules a mano lo que hace `compute_indicators.py`. El Koncorde encadena PVI, NVI, MFI, RSI, oscilador de Bollinger y estocástico sobre ventanas de 90 velas: estimarlo produce números con apariencia de precisión y sin ninguna. Lo mismo con el POC de un perfil de volumen, que sale de repartir el volumen de cada vela entre rangos de precio. Si por algún motivo no podés ejecutar el script, es mejor omitir esos bloques —las secciones se ocultan solas— que inventarlos.

## Datos

Usá, en este orden de preferencia:

1. **MCP de TradingView**, si está disponible en la sesión. Es la fuente más confiable para OHLCV e indicadores. Verificá primero qué herramientas hay disponibles antes de asumir que no está.
2. **Búsqueda web** (Yahoo Finance, Investing, StockAnalysis, Finviz, TradingView, el sitio del emisor) para precio, rango 52 semanas, volumen, P/E actual y forward, y confirmación de niveles.
3. **Datos que el usuario pegue** en el prompt — tienen prioridad sobre todo lo demás si hay conflicto, pero avisá del conflicto.

Reglas que importan:

- **La serie de precios es el corazón del informe. Conseguí ~450 velas diarias**, unos 22 meses. No es un capricho: la ventana de cálculo y la del gráfico son cosas distintas, y la que manda es la SMA200. Una SMA de 200 períodos necesita 200 velas para dar su **primer** valor, así que para que la línea recorra un gráfico de 250 velas hacen falta 250+199 de historia. Con 250 velas descargadas tendrías la SMA200 cubriendo apenas el 20% del gráfico; con 200 exactas, un solo punto; con menos, nada. Descargá de más y dejá que `--velas-grafico` recorte lo que se dibuja: el script calcula sobre todo lo que le pases y te avisa por stderr exactamente cuántas velas faltan si te quedaste corto. El Koncorde también agradece: usa ventanas de 90 y necesita ~130 para estabilizarse.
- **Si no llegás a 450, seguí adelante igual, pero decilo.** Con menos de 200 velas la serie `SMA200` sale entera en `null`, el gráfico no la dibuja y `medias_estado.sin_dato` la lista. En ese caso no la cites, no la infieras, topeá Tendencia en 21 y bajá la confianza a Media. Un régimen de largo plazo declarado sin la media que lo define es exactamente el tipo de número inventado que esta skill existe para evitar.
- Si solo podés recuperar cierres (sin OHLC), usá `cierres` y el gráfico se dibuja como línea, pero avisá que sin OHLC el perfil de volumen y el Koncorde pierden precisión. Si no conseguís ninguna serie, el informe igual se genera sin gráfico ni volumen institucional, y eso hay que decírselo al usuario explícitamente: el valor del entregable cae bastante.
- **El volumen ya no es opcional.** Sin `volumen` no hay perfil de volumen ni Koncorde, que son dos de las secciones más informativas. Si la fuente que estás usando no lo trae, buscá otra antes de resignarlo.
- **Marcá lo estimado.** Si un valor de RSI o un P/E forward lo derivaste o lo aproximaste en lugar de leerlo de una fuente, decilo en el campo `lectura` del indicador o en `fundamental.lectura`. Un número inventado con apariencia de precisión es el peor resultado posible: el usuario opera con esto.
- **Registrá las fuentes** en `meta.fuentes`. El footer las muestra.
- Si el usuario no dice el timeframe, asumí **diario como principal y semanal como contexto**, que es lo que pide el análisis multi-timeframe.

## Contrato de datos (`analisis.json`)

Estructura completa y comentada en `references/schema.md`. Consultala cuando dudes de un campo. El esqueleto:

```json
{
  "meta": {"ticker","nombre","sector","exchange","moneda","decimales","precio_actual",
           "variacion_dia_pct","fecha_analisis","horizonte","rango_52s":[min,max],"fuentes":[]},
  "resumen": {"score":0-100,"sesgo":"Alcista|Neutral|Bajista","confianza":"Alta|Media|Baja","tesis":"2-3 frases"},
  "scoring": [{"componente","peso","puntaje","nota"}],
  "tendencia": {"diario":{"direccion","estructura","comentario"},"semanal":{...},"confluencia"},
  "indicadores": [{"nombre","timeframe","valor","sesgo","que_mide","lectura","limitacion",
                   "escala":{"min","max","valor","dec","zonas":[{"desde","hasta","color"}]}}],
  "patrones": [{"nombre","timeframe","tipo","estado","objetivo","implicancia","sesgo"}],
  "niveles": {"soportes":[{"precio","fuerza","origen"}],"resistencias":[...]},
  "precio_serie": {"timeframe","fechas":[],"ohlc":[[o,h,l,c]],"cierres":[],"volumen":[],
                   "medias":{"WMA10":[],"WMA21":[],"EMA50":[],"SMA200":[]}},   // copiar de calculado.json
  "volume_profile": {"timeframe","ventana","bins":[{"desde","hasta","volumen","vol_alcista",
                     "vol_bajista","es_poc","en_value_area"}],"poc","val","vah",
                     "pct_en_value_area","sesgo_flujo","hvn":[],"lvn":[],"posicion_precio","lectura"},
  "koncorde": {"timeframe","fechas":[],"verde":[],"marron":[],"azul":[],"media":[],
               "azul_actual","verde_actual","marron_actual","media_actual",
               "azul_delta_10d","verde_delta_10d","picos_nevados","mar",
               "estado","detalle_auto","lectura","divergencia"},
  "fundamental": {"pe_actual","pe_forward","pe_sector","pe_historico_5a","eps_actual","eps_forward",
                  "crecimiento_eps_pct","prima_sector_pct","lectura","riesgo_valuacion"},
  "gestion_riesgo": {"entrada","zona_entrada":[a,b],"stop_loss","tp1","tp2","capital_ejemplo",
                     "invalidacion","gestion"},
  "escenarios": [{"nombre":"Alcista|Neutral|Bajista","probabilidad","objetivo","descripcion","disparadores"}],
  "conclusion": "texto, párrafos separados por línea en blanco",
  "riesgos": ["qué invalidaría la lectura"]
}
```

El script deriva solo: `riesgo_pct`, `rr_tp1`, `rr_tp2`, `retorno_pct` de escenarios y el score total desde `scoring`. No los escribas a mano salvo que quieras forzar un valor distinto.

Los `null` y las secciones ausentes se manejan solos: la sección se oculta. Preferí omitir un bloque antes que rellenarlo con datos falsos.

## Cómo llenar cada sección

**Resumen.** La `tesis` son 2-3 frases que un operador puede leer y actuar. Direccional y concreta: "Tendencia alcista intacta en semanal, pero el diario llegó sobrecomprado a la resistencia de 178. Esperar retroceso a la zona 168-170 antes de entrar." No: "El activo presenta señales mixtas que requieren monitoreo."

**Score.** Sale del desglose de `scoring`, con la rúbrica de `references/scoring.md` (tendencia 25, momentum 20, estructura de niveles 20, volumen 15, patrones 10, valuación 10). Cada componente lleva una `nota` de una línea que justifique el puntaje — es lo que hace auditable el número. Un score sin justificación es un número inventado con barra de progreso.

**Sesgo y confianza.** El sesgo sale del score (>60 alcista, 40-60 neutral, <40 bajista) y de la confluencia multi-timeframe. La confianza es otra cosa: mide cuán consistente es la evidencia. Diario y semanal alineados con volumen confirmando = Alta. Timeframes en conflicto, patrón sin confirmar o datos incompletos = Baja. Un score de 72 con confianza Baja es una combinación perfectamente válida y honesta.

**Indicadores.** Mínimo 5, típicamente RSI, MACD, medias móviles, ADX, volumen relativo, y opcionalmente estocástico, ATR o Bollinger. El indicador de medias va con `valor` tomado de `medias_estado.orden` y `lectura` que mencione el cruce rápido si hubo uno reciente. Para cada uno:
- `que_mide` es la explicación didáctica que aparece en el tooltip. Escribila para alguien que sabe operar pero no memoriza fórmulas. Hay textos base en `references/indicadores.md`.
- `lectura` es la interpretación **de este caso concreto**, con el número. "RSI en 68,4: momentum fuerte pero acercándose a sobrecompra; en las dos veces anteriores que superó 70 en los últimos 6 meses vino una corrección del 5-7%."
- `limitacion` (opcional pero valioso): cuándo este indicador miente. El RSI se queda pegado en sobrecompra durante tendencias fuertes; el MACD llega tarde en rangos laterales. Decirlo evita que el lector sobreinterprete.
- `escala` alimenta la barra visual. Solo tiene sentido para indicadores acotados (RSI 0-100, estocástico 0-100, ADX 0-60). Para MACD o precio, omitila.

**Perfil de volumen.** Los números salen del script; vos escribís `lectura`. La pregunta que tiene que contestar no es "dónde está el POC" —eso ya está en la tabla— sino qué implica para el plan: si el stop queda del lado seguro de un HVN o en medio de un vacío donde el precio no frena, si el TP1 coincide con una zona de alto volumen donde va a aparecer oferta, si el precio está operando arriba de la value area con poco volumen debajo sosteniéndolo. El detalle conceptual de POC, value area, HVN y LVN está en `references/indicadores.md`.

Un uso concreto que vale la pena: cuando un soporte que dibujaste por precio coincide con un HVN, subile la `fuerza` y decilo en el `origen` del nivel. Esa confluencia es de las pocas que agrega información real en lugar de repetir el mismo dato.

**Koncorde.** También sale del script. Lo primero que hay que mirar es el área azul, que es la mano fuerte: sobre cero y subiendo es acumulación, bajo cero y bajando es distribución. El verde es la mano débil y su valor está sobre todo en el contraste con el azul. El marrón vive en una banda positiva por construcción, así que no escribas nunca que "perdió el cero".

La `lectura` debe hablar del caso con los números: "el azul recuperó 25 puntos en diez ruedas pero sigue apenas bajo cero". Y si el precio hizo un extremo que el azul no acompañó, cargá `divergencia`: es la señal más accionable del indicador y merece su propio campo. El `estado` que propone el script podés corregirlo si el contexto lo justifica, pero tiene que seguir siendo coherente con `azul_actual` —el validador avisa si no lo es.

Ninguno de los dos va en el array `indicadores`: tienen su propia sección. Lo que sí conviene es que su lectura se refleje en la `nota` del componente Volumen del scoring.

**Patrones.** Solo los que realmente ves en la serie. Es mejor un array vacío — el template muestra un mensaje limpio — que inventar un hombro-cabeza-hombro. Distinguí `estado`: "confirmado" (rompió y validó), "en formación" (falta la ruptura), "invalidado". El `objetivo` es la proyección medida del patrón, no un deseo.

**Niveles.** 3-4 soportes y 3-4 resistencias, ordenados por relevancia. `origen` es lo que le da peso al nivel: "mínimo de octubre + EMA50 + zona de alto volumen". La EMA50 y la SMA200 son soportes dinámicos legítimos y conviene citarlas cuando el precio está cerca; el par rápido WMA10/WMA21 no lo es, sirve para timing, no para definir niveles. `fuerza` es fuerte/media/débil según cuántos toques respetó y cuánta confluencia tiene. El template calcula la distancia porcentual al precio actual.

**Valuación.** Solo P/E actual, forward, del sector y promedio histórico de 5 años, más EPS. El objetivo no es valuar la empresa sino responder una pregunta: ¿el múltiplo le deja aire al movimiento técnico o ya está descontando todo? Si el P/E forward es mucho menor al actual, el mercado espera crecimiento de ganancias, lo que apoya un sesgo alcista. Si el activo cotiza con prima fuerte sobre su sector y su historia, un breakout técnico tiene menos combustible. Usá `riesgo_valuacion` para el caso incómodo. Para índices, cripto o activos sin P/E significativo, omití el bloque entero.

**Gestión de riesgo.** El stop se pone donde la tesis se rompe (bajo el último mínimo relevante, bajo el soporte, bajo la media que sostiene), **no** a un porcentaje redondo arbitrario. Los TP van en niveles reales: TP1 en la primera resistencia, TP2 en la siguiente o en la proyección del patrón. Si al calcular el R/R te da menos de 1,5, el setup no es bueno — decilo en vez de mover el stop para maquillar el número. `invalidacion` es obligatoria en la práctica: describe el evento (no el precio) que mata la tesis. `gestion` sirve para reglas de manejo: mover a breakeven en TP1, tomar mitad, trailing por ATR.

**Escenarios.** Tres, sumando 100%. Las probabilidades deben ser coherentes con el sesgo y el score: un score de 78 con escenario alcista al 35% es contradictorio. Cada uno con `objetivo` de precio y `disparadores` observables ("cierre semanal sobre 182 con volumen sobre el promedio de 20 sesiones"), porque un escenario sin gatillo no es accionable.

**Conclusión.** Cierra el círculo: qué hacer, a qué precio, con qué riesgo, y qué mirar para cambiar de opinión. Párrafos separados por línea en blanco. Sin bullets.

## Calidad del entregable

Antes de entregar, revisá que:

- El script no haya tirado advertencias sin resolver (SL del lado equivocado, probabilidades que no suman 100, R/R pobre, score incoherente con el sesgo).
- El gráfico tenga suficientes velas para verse como un gráfico y no como cuatro puntos.
- Los niveles del plan caigan dentro del rango visible del gráfico — si el TP2 está al doble del precio, se ve mal y probablemente el objetivo sea poco realista.
- Cada indicador tenga su `que_mide` cargado, porque si no el tooltip queda vacío y se rompe el valor de la interactividad.
- Los números coincidan entre secciones: el precio del resumen, el último cierre de la serie y la base de los cálculos de retorno tienen que ser el mismo.
- El perfil de volumen y el Koncorde tengan su `lectura` escrita. Sin ella el lector ve dos gráficos lindos y no sabe qué hacer con ellos, que es exactamente el fracaso que estos indicadores deberían evitar.
- La lectura del volumen institucional no contradiga silenciosamente al resto del informe. Si el Koncorde marca distribución y el score da 75 con sesgo alcista, o lo explicás o revisás el score: es la clase de tensión que el lector merece ver planteada, no escondida.

El informe termina con un disclaimer legal automático. No lo dupliques en el chat ni recomiendes operar; presentá el análisis y dejá la decisión del lado del usuario.

## Archivos

- `scripts/compute_indicators.py` — calcula todos los indicadores desde la serie OHLCV, incluidos el perfil de volumen y el Koncorde. Opciones: `--velas-grafico` (velas que se dibujan, default 250, `0` para todas; el cálculo usa siempre la serie completa), `--vp-bins` (rangos del perfil, default 24), `--vp-ventana` (velas que cubre, default 120, `0` para todas), `--koncorde-cola` (puntos a exportar, default 120).
- `scripts/build_report.py` — render + validación. Ejecutalo siempre desde su ruta; encuentra el template solo.
- `assets/report_template.html` — el informe completo con CSS/JS/SVG inline. No hace falta leerlo para usar la skill; leelo solo si vas a modificar el diseño.
- `references/schema.md` — contrato de datos campo por campo, con ejemplo completo.
- `references/scoring.md` — rúbrica del score técnico 0-100.
- `references/indicadores.md` — textos base de `que_mide`, umbrales y limitaciones de cada indicador, más la guía conceptual de perfil de volumen y Koncorde.
