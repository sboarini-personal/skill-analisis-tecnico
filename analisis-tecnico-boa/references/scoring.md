# Rúbrica del Score Técnico (0-100)

El score existe para comprimir el análisis en un número comparable entre activos y entre fechas. Solo sirve si es reproducible: dos análisis del mismo gráfico deberían dar puntajes parecidos. Por eso cada componente tiene criterios explícitos y cada puntaje asignado lleva una `nota` que lo justifica.

Interpretación de la escala: 0-25 bajista fuerte, 25-40 bajista, 40-60 neutral, 60-75 alcista, 75-100 alcista fuerte.

El array `scoring` del JSON debe tener exactamente estos seis componentes, con estos pesos (suman 100).

## 1. Tendencia — peso 25

Mide la dirección estructural y su alineación entre marcos temporales. Es el componente más pesado porque operar contra la tendencia dominante es el error más caro.

Se puntúa con dos capas. El **régimen** lo define el par estructural EMA50/SMA200: es lo que fija la banda. El **giro** lo aporta el par rápido WMA10/WMA21 sobre gráfico diario: modula dentro de la banda y, con confluencia suficiente, permite moverse a la banda contigua. Los datos salen del bloque `medias_estado` del script (`orden`, `alineacion`, `pendiente_10d_pct`, `cruce_rapido`, `cruce_estructural`), no de estimar a ojo.

| Puntaje | Situación |
|---|---|
| 22-25 | Alcista en diario y semanal. Máximos y mínimos crecientes intactos. Abanico completo: precio > WMA10 > WMA21 > EMA50 > SMA200, con EMA50 sobre SMA200 y ambas con pendiente positiva. |
| 17-21 | Alcista dominante con alguna grieta: el par rápido cruzó a la baja pero el estructural sigue alcista, la pendiente de la EMA50 se aplana, un mínimo creciente quedó comprometido, o semanal alcista con diario en corrección. |
| 11-16 | Lateral, sin estructura direccional clara, medias entrelazadas, el par rápido cruzando de un lado al otro sin separación, o timeframes en conflicto abierto. |
| 5-10 | Bajista dominante con algún signo de agotamiento: divergencias, pérdida de momentum vendedor, base en formación, o cruce alcista reciente del par rápido todavía sin confirmar. |
| 0-4 | Bajista en diario y semanal, máximos y mínimos decrecientes, abanico invertido con precio bajo las cuatro medias, EMA50 bajo SMA200 y pendientes negativas. |

**El cruce del par rápido como cambio temprano de tendencia.** Es la lectura para la que está el par, y es donde el componente se gana el peso 25 en vez de limitarse a describir el pasado. Un cruce de WMA10 sobre WMA21 en un régimen bajista es la primera pista de que el piso se está formando; el cruce inverso en régimen alcista es la primera pista de distribución. Pero aislado no vale: en lateral ese cruce ocurre varias veces por mes.

La regla es de confluencia, y el mínimo son **dos confirmaciones de tres** entre Koncorde, MACD y RSI, evaluadas sobre el mismo gráfico diario:

- **Koncorde** — el azul (mano fuerte) se mueve en la misma dirección del cruce. Un cruce alcista con `azul_delta_10d` positivo y azul cruzando sobre cero es la confirmación más fuerte de las tres, porque dice quién está del otro lado.
- **MACD** — el histograma gira y la línea cruza su señal en el mismo sentido, mejor todavía si el cruce del MACD viene del lado correcto del cero.
- **RSI** — recupera 50 hacia arriba en el cruce alcista, o lo pierde hacia abajo en el bajista. Una divergencia previa en el sentido del cruce lo refuerza.

Con dos de tres confirmando, el cruce mueve el puntaje una banda entera respecto de lo que dictaría el régimen solo, y hay que decirlo explícito en la `nota` nombrando qué confirmó. Con una sola confirmación, se queda dentro de la banda del régimen pero se corre al extremo que corresponda. Sin ninguna, no toca el puntaje: es ruido de lateral y conviene aclararlo, porque el lector va a ver el cruce en el gráfico y merece saber por qué no se le dio peso.

Dos condiciones que invalidan la lectura del cruce sin importar la confluencia: ADX bajo 20, porque sin tendencia que medir el cruce no proyecta nada, y una separación entre ambas medias que oscile alrededor de cero en las últimas ruedas en vez de abrirse, que es la firma de un mercado sin dirección.

Y una asimetría que hay que respetar: el par rápido **nunca sobrescribe al estructural**. Un cruce alcista confirmado con la EMA50 bajo la SMA200 llega como mucho a la banda 11-16, porque sigue siendo un rebote dentro de una tendencia bajista de largo plazo hasta que el precio recupere la SMA200. El componente mide tendencia, no rebotes.

Si la serie tiene menos de 200 velas, el script lo avisa y lista la SMA200 en `medias_estado.sin_dato`. En ese caso no la cites ni la infieras: puntuá el régimen con la EMA50 como referencia estructural, no asignes más de 21 aunque todo lo demás esté alineado, y declará confianza Media a lo sumo. Es exactamente la clase de dato faltante que la confianza está para reportar.

## 2. Momentum — peso 20

Mide la fuerza del movimiento actual: RSI, MACD, estocástico, ADX y las divergencias entre precio e indicador.

| Puntaje | Situación |
|---|---|
| 17-20 | RSI 55-70 con pendiente positiva, MACD sobre su señal y sobre cero, ADX > 25 confirmando la dirección. Sin divergencias bajistas. |
| 13-16 | Momentum positivo pero con una advertencia: RSI > 70 (sobrecompra), o ADX débil, o MACD perdiendo separación. |
| 8-12 | Indicadores en zona neutra o contradiciéndose entre sí. ADX < 20: no hay tendencia que medir. |
| 4-7 | Momentum negativo pero con signos de giro: RSI saliendo de sobreventa, divergencia alcista, histograma del MACD contrayéndose. |
| 0-3 | RSI < 40 y cayendo, MACD bajo señal y bajo cero, ADX confirmando tendencia bajista, divergencias bajistas activas. |

Las divergencias pesan: una divergencia bajista clara (precio hace máximo mayor, RSI hace máximo menor) baja el puntaje al menos 4 puntos aunque los indicadores estén en zona positiva.

## 3. Estructura de niveles — peso 20

Mide dónde está el precio respecto de sus soportes y resistencias, que es lo que determina el riesgo asimétrico de entrar hoy.

| Puntaje | Situación |
|---|---|
| 17-20 | Precio apoyado sobre un soporte fuerte con la resistencia lejos: mucho recorrido arriba, poco riesgo abajo. O ruptura de resistencia confirmada con retest exitoso. |
| 13-16 | Precio en la mitad inferior del rango, con soportes cercanos definidos. |
| 8-12 | Precio en mitad de rango, equidistante. Sin ventaja de ubicación. |
| 4-7 | Precio pegado a una resistencia fuerte con el soporte lejos: riesgo asimétrico en contra. |
| 0-3 | Ruptura bajista de soporte relevante confirmada, con el siguiente soporte muy por debajo. |

La distancia importa tanto como la existencia del nivel. Un soporte fuerte 12% abajo no protege nada hoy.

## 4. Volumen — peso 15

El volumen es lo que separa un movimiento real de un ruido. Este componente integra tres lecturas distintas del mismo dato: si el volumen acompaña la dirección (volumen relativo), dónde se negoció (perfil de volumen) y quién lo negoció (Koncorde).

| Puntaje | Situación |
|---|---|
| 13-15 | Volumen expandiendo en las subas y contrayéndose en las bajas. Rupturas con volumen muy sobre el promedio de 20 sesiones. Precio sobre el POC con la value area actuando de soporte. Koncorde con azul sobre cero y subiendo. |
| 10-12 | Volumen normal, sin desmentir la tendencia pero sin confirmarla con fuerza. Precio dentro de la value area. Koncorde sin sesgo claro de mano fuerte. |
| 6-9 | Volumen plano o irrelevante. Rupturas con volumen flojo (señal clásica de falsa ruptura). Precio atrapado en un LVN, sin volumen que lo sostenga. |
| 3-5 | Volumen creciendo en las bajas. Azul del Koncorde cayendo bajo cero mientras el verde sube: distribución. Precio bajo el POC intentando recuperarlo sin éxito. |
| 0-2 | Capitulación vendedora con volumen extremo, o divergencia severa entre precio y flujo: precio en máximos con el azul del Koncorde marcando mínimos decrecientes. |

Cómo combinar las tres señales sin doble contar: el volumen relativo dice si hoy hubo convicción, el perfil dice si el precio está en zona defendida o en el vacío, y el Koncorde dice de qué lado del libro estuvo el dinero grande. Cuando las tres coinciden, movete al extremo del rango de puntaje. Cuando el perfil y el Koncorde se contradicen — precio sobre el POC pero con el azul cayendo — quedate en el medio y explicá la contradicción en la `nota`, porque esa tensión suele resolverse en contra del precio.

Si no tenés datos de volumen confiables, asigná 7-8 y aclaralo en la `nota`. No lo inventes.

## 5. Patrones — peso 10

| Puntaje | Situación |
|---|---|
| 9-10 | Patrón alcista confirmado con ruptura y volumen (taza con asa, doble piso, bandera alcista, triángulo ascendente roto). |
| 6-8 | Patrón alcista en formación, sin ruptura todavía. |
| 4-5 | Sin patrones identificables. Este es el valor por defecto y es perfectamente normal. |
| 2-3 | Patrón bajista en formación. |
| 0-1 | Patrón bajista confirmado con ruptura (hombro-cabeza-hombro, doble techo, bandera bajista). |

Resistí la tentación de ver patrones en todos lados. Un 4-5 honesto vale más que un patrón forzado que después contamina el sesgo.

## 6. Valuación — peso 10

La capa fundamental mínima. Responde si el múltiplo le deja aire al movimiento técnico.

| Puntaje | Situación |
|---|---|
| 9-10 | P/E forward bastante menor al actual (ganancias creciendo) y con descuento contra el sector y contra su propio promedio de 5 años. |
| 7-8 | Múltiplos en línea con el sector y con la historia del activo. |
| 4-6 | Prima moderada sobre el sector, justificable por crecimiento. |
| 2-3 | Prima fuerte sobre sector e historia, con EPS forward plano o cayendo. |
| 0-1 | Múltiplo extremo o sin ganancias, con deterioro en las estimaciones. |

Si el activo no tiene P/E significativo (índices amplios, cripto, commodities, empresas sin ganancias), asigná 5 (neutral) y explicá en la `nota` que la valuación no aplica. No castigues ni premies por falta de dato.

## Coherencia final

Después de sumar, verificá tres cosas antes de escribir el JSON:

El score y el sesgo tienen que apuntar al mismo lado. Un 72 con sesgo bajista significa que algo se puntuó mal o que el sesgo está mal declarado.

Las probabilidades de los escenarios tienen que ser coherentes con el score. Como referencia aproximada: con score 75+, el escenario alcista debería estar en torno al 55-65%; con score 45-55, los tres escenarios deberían quedar razonablemente repartidos; con score bajo 30, el bajista debería dominar. No es una fórmula, pero una desviación grande necesita justificación explícita en la descripción del escenario.

La confianza no depende del score sino de la consistencia de la evidencia. Score alto con timeframes en conflicto, o con datos que tuviste que estimar, es confianza Media o Baja. Decirlo es más útil que aparentar certeza.
