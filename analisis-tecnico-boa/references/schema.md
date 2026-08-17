# Contrato de datos: `analisis.json`

Todo lo que el informe muestra sale de este archivo. El template no inventa nada: si un campo falta, la sección se oculta o muestra un mensaje neutro. Preferí omitir antes que rellenar con datos falsos.

Índice: [meta](#meta) · [resumen](#resumen) · [scoring](#scoring) · [tendencia](#tendencia) · [indicadores](#indicadores) · [patrones](#patrones) · [niveles](#niveles) · [precio_serie](#precio_serie) · [fundamental](#fundamental) · [gestion_riesgo](#gestion_riesgo) · [escenarios](#escenarios) · [conclusion y riesgos](#conclusion-y-riesgos) · [ejemplo](#ejemplo-minimo-completo)

---

## meta

| Campo | Tipo | Notas |
|---|---|---|
| `ticker` | string | Como cotiza: `NVDA`, `YPFD.BA`, `BTCUSD` |
| `nombre` | string | Razón social o nombre del activo |
| `sector` | string | Aparece como chip bajo el ticker |
| `exchange` | string | NASDAQ, NYSE, BYMA, Binance… |
| `moneda` | string | `USD`, `ARS`, `EUR`, `BRL`, `GBP`. Define el símbolo que se muestra |
| `decimales` | int | Decimales por defecto para precios. 2 típico; 4-6 para cripto de bajo precio |
| `precio_actual` | number | Último cierre. Debe coincidir con el último valor de `precio_serie` |
| `variacion_dia_pct` | number | Variación de la jornada en % (`-1.34`) |
| `fecha_analisis` | string | `YYYY-MM-DD` o texto legible |
| `horizonte` | string | `"2-8 semanas"`, `"swing"`, `"intradía"` |
| `rango_52s` | [min, max] | Rango de 52 semanas |
| `fuentes` | array | Strings o `{"nombre","url"}`. Se listan en el footer |

## resumen

| Campo | Tipo | Notas |
|---|---|---|
| `score` | 0-100 | Si hay `scoring`, el script lo recalcula desde el desglose |
| `sesgo` | string | `Alcista` / `Neutral` / `Bajista`. Define el color de todo el informe |
| `confianza` | string | `Alta` / `Media` / `Baja` |
| `tesis` | string | 2-3 frases accionables. Es lo primero que se lee |

## scoring

Array de exactamente seis objetos cuyos `peso` suman 100. Ver `scoring.md` para los criterios.

```json
{"componente":"Tendencia","peso":25,"puntaje":21,
 "nota":"Alcista en semanal y diario; EMA50 sobre SMA200 con pendiente positiva y abanico ordenado, pero el último mínimo creciente quedó justo."}
```

La `nota` es lo que hace auditable el puntaje. Sin ella el score es un número sin respaldo.

## tendencia

Objeto con claves opcionales `intradiario`, `diario`, `semanal`, `mensual`, más `confluencia` (string). Cada marco:

```json
"semanal": {"direccion":"Alcista","estructura":"Máximos y mínimos crecientes desde abril",
            "comentario":"Canal ascendente intacto; el precio trabaja en el tercio superior."}
```

`direccion` determina el color del tag. `confluencia` explica qué pasa cuando los marcos no coinciden — es donde el análisis multi-timeframe agrega valor real.

## indicadores

Array. Mínimo 5. Textos base en `indicadores.md`.

| Campo | Notas |
|---|---|
| `nombre` | Incluí el parámetro: `"RSI (14)"` |
| `timeframe` | `"Diario"`, `"Semanal"` |
| `valor` | **String**, no número. Permite `"1,8x prom. 20d"` o `"P > WMA10 > WMA21 > EMA50 > SMA200"` |
| `sesgo` | `alcista` / `neutral` / `bajista`. Colorea el valor y el tag |
| `que_mide` | Explicación didáctica → tooltip. Sin esto el tooltip queda vacío |
| `lectura` | Interpretación **de este caso**, con el número concreto |
| `limitacion` | Opcional. Cuándo este indicador engaña |
| `escala` | Solo para indicadores acotados. `{"min","max","dec","valor","zonas":[...]}` |

En `zonas`, `color` ∈ `bull` / `bear` / `neut`, y se pinta según lo que la zona implica operativamente (sobreventa del RSI = `bull`), no según si el número es alto o bajo.

## patrones

Array; puede ir vacío y el template lo resuelve con un mensaje limpio.

```json
{"nombre":"Bandera alcista","timeframe":"Diario","tipo":"continuación",
 "estado":"en formación","objetivo":198.40,"sesgo":"alcista",
 "implicancia":"Ruptura sobre 182 proyecta el mástil previo (~16 puntos)."}
```

`estado` ∈ `confirmado` / `en formación` / `invalidado` — define el color del tag.

## niveles

```json
{"soportes":[{"precio":168.20,"fuerza":"fuerte","origen":"Mínimo de octubre + EMA50 + alto volumen"}],
 "resistencias":[{"precio":182.00,"fuerza":"media","origen":"Máximo de julio"}]}
```

`fuerza` ∈ `fuerte` / `media` / `débil` → tres puntos rellenos, dos o uno. El template ordena por cercanía y calcula la distancia porcentual al precio actual. Apuntá a 3-4 de cada lado.

## precio_serie

El bloque más importante para el valor visual del informe.

| Campo | Notas |
|---|---|
| `timeframe` | `"Diario"` |
| `fechas` | Array de `"YYYY-MM-DD"`. **Todos los demás arrays deben tener esta misma longitud** |
| `ohlc` | `[[open, high, low, close], ...]` → dibuja velas japonesas |
| `cierres` | Alternativa a `ohlc` → dibuja línea con área. Si están los dos, gana `ohlc` |
| `volumen` | Array de números → barras coloreadas bajo el precio |
| `medias` | `{"WMA10":[...], "WMA21":[...], "EMA50":[...], "SMA200":[...]}`. Usá `null` en las posiciones sin dato suficiente |

**Este bloque no lo armás vos: sale entero de `scripts/compute_indicators.py`, bajo la clave `precio_serie`.** Copialo tal cual. Viene con las cuatro medias ya calculadas y todos los arrays recortados a la misma ventana, de modo que la vela *i* y el valor *i* de cada media corresponden a la misma fecha. Rearmarlo a mano, o pegarle velas de otra fuente, rompe esa correspondencia sin que nada avise.

**La ventana de cálculo no es la ventana del gráfico.** El script calcula sobre toda la serie que le pases y después recorta a las últimas `--velas-grafico` (default 250, `0` = todas). Esa separación existe por la SMA200: necesita 200 velas para producir su **primer** valor, así que para dibujarla completa sobre un gráfico de N velas hacen falta **N+199** de historia — unas 450 para las 250 por defecto. Con 250 descargadas la SMA200 cubre apenas el 20% del gráfico; con menos de 200, la serie viene entera en `null` y el gráfico no la dibuja. El script avisa por stderr en ambos casos y te dice cuántas velas faltan.

En el gráfico, 90 a 250 velas es el rango legible: menos de 30 se ve pobre, más de 400 comprime demasiado las velas. Eso aplica a lo que se **dibuja**, no a lo que se descarga — descargar de más no tiene costo visual.

El orden de las claves de `medias` define el orden de la leyenda y de los colores, así que respetalo: rápida a lenta. Cada serie trae `null` en sus primeras N-1 posiciones, y una serie entera en `null` se omite de la leyenda sin dejar hueco.

## medias_estado (solo lectura, no va al JSON)

`compute_indicators.py` devuelve además un bloque `medias_estado` que **no forma parte de `analisis.json`**: es material para que puntúes Tendencia y redactes el indicador de medias sin estimar nada a ojo.

| Campo | Qué trae |
|---|---|
| `orden` | El abanico como texto, listo para usar de `valor` del indicador: `"P > WMA10 > WMA21 > EMA50 > SMA200"` |
| `alineacion` | `alcista_completa` / `bajista_completa` / `mixta`, con sufijo `_parcial` si falta alguna media por datos |
| `sin_dato` | Medias sin valor por serie corta. Si aparece `SMA200`, no la cites en el informe |
| `actuales`, `distancia_pct` | Valor de cada media y distancia porcentual del precio a cada una |
| `pendiente_10d_pct` | Variación porcentual de cada media en las últimas 10 velas: es la pendiente, medida |
| `cruce_rapido` | Último cruce WMA10/WMA21: `tipo`, `fecha`, `velas_desde`, `separacion_pct` actual |
| `cruce_estructural` | Último cruce EMA50/SMA200 — el dorado o el de la muerte — con los mismos campos |

`null` en un cruce significa que no hubo ninguno en la historia disponible, lo cual también es información: una tendencia sin cruces es una tendencia que no se interrumpió.

## volume_profile

Generalo con `scripts/compute_indicators.py`, no a mano: el reparto del volumen de cada vela entre los rangos de precio y la expansión de la value area son mecánicos y fáciles de arruinar estimando. Lo único que escribís vos es `lectura`.

| Campo | Notas |
|---|---|
| `timeframe`, `ventana` | Sobre cuántas velas se construyó. Declararlo importa: el POC cambia mucho con la ventana |
| `bins` | Array de `{desde, hasta, volumen, vol_alcista, vol_bajista, es_poc, en_value_area}`. 20-30 rangos es el punto útil |
| `poc` | Precio de mayor volumen. Debe caer entre `val` y `vah` |
| `val`, `vah` | Extremos de la value area |
| `pct_en_value_area` | Porcentaje real del volumen que cae en la value area (≈70, algo más porque se agregan rangos enteros) |
| `sesgo_flujo` | Porcentaje del volumen ejecutado en velas alcistas |
| `hvn`, `lvn` | Arrays de `{desde, hasta, pct_del_total}`. Zonas de alto y de bajo volumen |
| `posicion_precio` | Texto: dónde cae el precio actual respecto de la value area |
| `lectura` | **Lo escribís vos.** Qué implica el perfil para el plan: dónde hay soporte real, dónde hay vacío, qué nivel del plan coincide con un HVN |

`vol_alcista` y `vol_bajista` pintan cada barra en dos colores (comprador/vendedor). Si no los tenés, omitilos y la barra se dibuja en un solo color.

## koncorde

También sale de `scripts/compute_indicators.py`. Escribís `lectura` y, si aplica, `divergencia`.

| Campo | Notas |
|---|---|
| `timeframe` | `"Diario"` |
| `fechas` | Array propio, normalmente los últimos 120 puntos válidos. Puede ser más corto que `precio_serie.fechas` porque el indicador necesita ~130 velas de warm-up |
| `verde`, `marron`, `azul`, `media` | Arrays de la misma longitud que `fechas`. Admiten `null` en los huecos |
| `azul_actual`, `verde_actual`, `marron_actual`, `media_actual` | Últimos valores, para la tabla de lectura |
| `azul_delta_10d`, `verde_delta_10d` | Variación en las últimas 10 ruedas. Es lo que distingue acumulación de "posicionado" |
| `picos_nevados`, `mar` | Máximo y mínimo histórico del marrón, las referencias que usan los operadores de Blai5 |
| `estado` | `"Acumulacion"`, `"Distribucion"`, `"Posicionado"` o `"Neutral"`. El script lo propone; podés corregirlo si el contexto lo justifica, pero tiene que ser coherente con `azul_actual` (el validador avisa si no) |
| `detalle_auto` | Frase que genera el script explicando el estado |
| `lectura` | **Lo escribís vos.** La interpretación del caso, con números |
| `divergencia` | Opcional pero muy valioso: si el precio hace un extremo que el azul no acompaña, describilo acá |

Recordá que `marron` no cruza cero por construcción; no escribas lecturas del tipo "el marrón perdió el cero".

## fundamental

Omitir el bloque entero si el activo no tiene P/E significativo (índices, cripto, commodities).

| Campo | Notas |
|---|---|
| `pe_actual`, `pe_forward` | Núcleo del bloque |
| `pe_sector`, `pe_historico_5a` | Contexto comparativo; el gráfico de barras los enfrenta |
| `eps_actual`, `eps_forward` | En moneda |
| `crecimiento_eps_pct` | Implícito entre EPS actual y forward |
| `prima_sector_pct` | Positivo = cotiza con prima sobre el sector |
| `lectura` | Callout azul: qué implica el múltiplo para el setup técnico |
| `riesgo_valuacion` | Callout rojo. Solo si hay un riesgo concreto |

## gestion_riesgo

| Campo | Notas |
|---|---|
| `entrada` | Precio de referencia; alimenta la calculadora y el simulador |
| `zona_entrada` | `[min, max]`. Se pinta como banda azul en el gráfico |
| `stop_loss` | Donde la tesis se rompe, no un % redondo |
| `tp1`, `tp2` | En niveles reales de resistencia o proyección de patrón |
| `capital_ejemplo` | Precarga la calculadora. Default 10000 |
| `invalidacion` | El **evento** que mata la tesis, no solo el precio |
| `gestion` | Reglas de manejo: breakeven, toma parcial, trailing |

Derivados por el script: `riesgo_pct`, `rr_tp1`, `rr_tp2`. No los escribas salvo que quieras forzarlos.

## escenarios

Array de tres, con `probabilidad` sumando 100.

```json
{"nombre":"Alcista","probabilidad":45,"objetivo":198.00,
 "descripcion":"Ruptura de 182 con volumen y continuidad hacia el objetivo de la bandera.",
 "disparadores":"Cierre diario sobre 182 con volumen >1,3x el promedio de 20 sesiones."}
```

El campo `nombre` debe contener "Alcista", "Neutral" o "Bajista" porque de ahí sale el color del donut. `retorno_pct` lo calcula el script contra la entrada.

## conclusion y riesgos

`conclusion` es un string; los párrafos se separan con línea en blanco (`\n\n`). Sin bullets.

`riesgos` es un array de strings: qué invalidaría la lectura. Eventos concretos (resultados, macro, cambios regulatorios, correlaciones), no generalidades.

---

## Ejemplo mínimo completo

```json
{
  "meta": {
    "ticker": "NVDA", "nombre": "NVIDIA Corporation", "sector": "Semiconductores",
    "exchange": "NASDAQ", "moneda": "USD", "decimales": 2,
    "precio_actual": 176.42, "variacion_dia_pct": -0.85,
    "fecha_analisis": "2026-08-15", "horizonte": "4-8 semanas",
    "rango_52s": [86.62, 184.48],
    "fuentes": [{"nombre":"Yahoo Finance","url":"https://finance.yahoo.com/quote/NVDA"}]
  },
  "resumen": {
    "score": 71, "sesgo": "Alcista", "confianza": "Media",
    "tesis": "Tendencia alcista intacta en semanal con el precio consolidando bajo el máximo histórico. El momentum se enfrió sin romper estructura. Zona de entrada 170-173 con stop bajo 165."
  },
  "scoring": [
    {"componente":"Tendencia","peso":25,"puntaje":22,"nota":"Alcista en diario y semanal, abanico completo P > WMA10 > WMA21 > EMA50 > SMA200 con pendientes positivas."},
    {"componente":"Momentum","peso":20,"puntaje":13,"nota":"RSI 58 saliendo de sobrecompra; histograma del MACD contrayéndose."},
    {"componente":"Estructura de niveles","peso":20,"puntaje":14,"nota":"Precio en mitad alta del rango, soporte fuerte 4,7% abajo."},
    {"componente":"Volumen","peso":15,"puntaje":11,"nota":"Volumen normal, sin distribución evidente."},
    {"componente":"Patrones","peso":10,"puntaje":6,"nota":"Bandera alcista en formación, sin ruptura."},
    {"componente":"Valuación","peso":10,"puntaje":5,"nota":"P/E forward 32 vs 41 actual; prima sobre el sector justificada por crecimiento de EPS."}
  ],
  "tendencia": {
    "diario": {"direccion":"Neutral","estructura":"Rango 168-182","comentario":"Consolidación lateral tras el impulso de julio."},
    "semanal": {"direccion":"Alcista","estructura":"Máximos y mínimos crecientes","comentario":"Canal ascendente intacto desde abril."},
    "confluencia": "Semanal manda: la consolidación diaria es una pausa dentro de tendencia mayor, no un techo. Operar largo en retrocesos."
  },
  "indicadores": [
    {"nombre":"RSI (14)","timeframe":"Diario","valor":"58,3","sesgo":"neutral",
     "que_mide":"Compara la magnitud de las subas recientes contra la de las bajas para medir la fuerza del movimiento.",
     "lectura":"58,3 tras haber tocado 74 a fines de julio: enfriamiento ordenado sin perder la zona alcista de 45-50.",
     "limitacion":"En tendencias fuertes puede quedar sobre 70 semanas sin que el precio corrija.",
     "escala":{"min":0,"max":100,"dec":0,"valor":58.3,
       "zonas":[{"desde":0,"hasta":30,"color":"bull"},{"desde":30,"hasta":70,"color":"neut"},{"desde":70,"hasta":100,"color":"bear"}]}}
  ],
  "patrones": [
    {"nombre":"Bandera alcista","timeframe":"Diario","tipo":"continuación","estado":"en formación",
     "objetivo":198.40,"sesgo":"alcista","implicancia":"Ruptura sobre 182 proyecta el mástil previo."}
  ],
  "niveles": {
    "soportes":[{"precio":168.20,"fuerza":"fuerte","origen":"Base del rango + EMA50"},
                {"precio":158.00,"fuerza":"media","origen":"Mínimo de junio"}],
    "resistencias":[{"precio":182.00,"fuerza":"fuerte","origen":"Techo del rango, tres rechazos"},
                    {"precio":184.48,"fuerza":"media","origen":"Máximo histórico"}]
  },
  "precio_serie": {
    "timeframe":"Diario",
    "fechas":["2026-08-13","2026-08-14","2026-08-15"],
    "ohlc":[[174.10,177.80,173.50,177.20],[177.30,179.10,175.90,177.90],[177.60,178.40,175.20,176.42]],
    "volumen":[182000000,164000000,151000000],
    "medias":{"WMA10":[178.40,178.95,179.60],"WMA21":[175.10,175.48,175.90],
              "EMA50":[171.20,171.55,171.90],"SMA200":[148.30,148.70,149.10]}
  },
  "fundamental": {
    "pe_actual":41.2,"pe_forward":32.4,"pe_sector":28.6,"pe_historico_5a":45.1,
    "eps_actual":4.28,"eps_forward":5.45,"crecimiento_eps_pct":27.3,"prima_sector_pct":44.1,
    "lectura":"El forward muy por debajo del actual indica que el mercado descuenta fuerte crecimiento de ganancias, lo que le da soporte fundamental al sesgo técnico alcista.",
    "riesgo_valuacion":"La prima del 44% sobre el sector deja poco margen: un trimestre por debajo de estimaciones comprime el múltiplo antes que el gráfico reaccione."
  },
  "gestion_riesgo": {
    "entrada":171.50,"zona_entrada":[170.00,173.00],"stop_loss":165.00,
    "tp1":182.00,"tp2":198.00,"capital_ejemplo":10000,
    "invalidacion":"Cierre diario bajo 165 con volumen sobre el promedio: pierde la base del rango y la EMA50, y la estructura de mínimos crecientes queda rota.",
    "gestion":"Tomar la mitad en TP1 y mover el stop a breakeven. El resto con trailing de 2 ATR."
  },
  "escenarios": [
    {"nombre":"Alcista","probabilidad":45,"objetivo":198.00,
     "descripcion":"Ruptura de 182 con volumen y extensión hacia el objetivo de la bandera.",
     "disparadores":"Cierre diario sobre 182 con volumen >1,3x el promedio de 20 sesiones."},
    {"nombre":"Neutral","probabilidad":35,"objetivo":175.00,
     "descripcion":"Continúa el rango 168-182 durante varias semanas más.",
     "disparadores":"Rechazos sucesivos en 182 sin perder 168."},
    {"nombre":"Bajista","probabilidad":20,"objetivo":158.00,
     "descripcion":"Pérdida de 168 y búsqueda del mínimo de junio.",
     "disparadores":"Cierre bajo 168 con volumen creciente y RSI perforando 45."}
  ],
  "conclusion": "El activo mantiene tendencia alcista de fondo y lo que se ve en el diario es una pausa, no un techo.\n\nLa entrada tiene mejor relación riesgo-beneficio en la zona baja del rango que persiguiendo el precio actual.",
  "riesgos": [
    "Presentación de resultados dentro del horizonte del análisis: puede generar un gap que salte el stop.",
    "La prima de valuación amplifica cualquier revisión a la baja de estimaciones."
  ]
}
```
