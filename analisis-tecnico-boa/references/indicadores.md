# Indicadores: textos base, umbrales y limitaciones

Este archivo es material de apoyo para llenar el array `indicadores` del JSON. Los textos de `que_mide` son didácticos y aparecen en el tooltip al pasar el cursor: podés usarlos tal cual o adaptarlos. Lo que **no** se copia es `lectura`, que siempre tiene que hablar del caso concreto con el número real.

Cada bloque incluye la `escala` sugerida para la barra visual. Solo los indicadores acotados llevan escala; para MACD, ATR o precio, omitila.

---

## RSI (14)

**que_mide:** "Compara la magnitud de las subas recientes contra la de las bajas para medir la fuerza del movimiento. Se mueve entre 0 y 100. Sobre 70 el activo se considera sobrecomprado, bajo 30 sobrevendido. Más importante que los extremos es la zona en la que suele rebotar: en tendencias alcistas el RSI rara vez baja de 40, y en bajistas rara vez supera 60."

**Umbrales:** >70 sobrecompra (bajista de corto), 55-70 momentum alcista sano, 45-55 neutral, 30-45 momentum débil, <30 sobreventa (alcista de corto).

**limitacion:** "En tendencias fuertes el RSI puede quedar sobre 70 durante semanas sin que el precio corrija. Leído aislado como señal de venta genera salidas prematuras."

**escala:** `{"min":0,"max":100,"dec":0,"zonas":[{"desde":0,"hasta":30,"color":"bull"},{"desde":30,"hasta":70,"color":"neut"},{"desde":70,"hasta":100,"color":"bear"}]}`

Nota sobre los colores de la escala: las zonas se pintan por lo que implican operativamente. Sobreventa es zona de oportunidad de compra (verde), sobrecompra es zona de riesgo (roja).

---

## MACD (12,26,9)

**que_mide:** "Mide la distancia entre dos medias móviles exponenciales, de 12 y 26 períodos. Cuando la línea MACD cruza por encima de su señal de 9 períodos indica que el impulso alcista se acelera; por debajo, lo contrario. El histograma muestra esa distancia: si se agranda el movimiento gana fuerza, si se achica la pierde aunque el precio siga subiendo."

**Lectura:** posición respecto de la señal (cruce alcista o bajista), posición respecto de cero (tendencia de fondo), y dirección del histograma (aceleración o agotamiento).

**limitacion:** "Es un indicador rezagado: confirma movimientos ya iniciados. En mercados laterales da cruces falsos continuamente."

**escala:** omitir (no está acotado).

---

## Medias móviles (WMA 10/21, EMA 50, SMA 200)

Son cuatro medias con dos roles distintos, y no hay que mezclarlos. El par rápido **WMA10/WMA21** es el gatillo de swing sobre gráfico diario: su cruce es la señal temprana de cambio de tendencia. El par estructural **EMA50/SMA200** define el régimen y funciona como soporte o resistencia dinámica.

La elección de ponderación no es decorativa. La WMA pesa linealmente: el cierre de hoy vale 10 y el de hace diez ruedas vale 1, y lo que sale de la ventana se descarta de golpe. Reacciona antes que la SMA del mismo largo y también antes que la EMA, que arrastra toda la historia con peso decreciente. Sobre 10 y 21 sesiones eso es exactamente lo que se busca: detectar el giro temprano. Sobre 50 y 200 no, porque ahí lo que se quiere es estabilidad, y por eso la EMA50 y la SMA200 conservan la construcción tradicional que todo el mercado mira.

**que_mide:** "Cuatro medias con dos funciones. El par rápido WMA10/WMA21 pondera linealmente los cierres, así que reacciona antes que una media simple: su cruce es la primera señal de que la tendencia de corto plazo cambió de mano. El par estructural EMA50/SMA200 marca el régimen de mediano y largo plazo — el cruce dorado y el cruce de la muerte salen de ahí — y además actúa como soporte y resistencia dinámica, porque son los niveles que mira todo el mercado. Cuando las cuatro se ordenan en abanico con el precio arriba, la tendencia está alineada en todos los plazos."

**Cargá el valor como texto compuesto**, tomándolo de `medias_estado.orden` que devuelve el script: `"P > WMA10 > WMA21 > EMA50 > SMA200"`, o algo como `"WMA10 cruzó sobre WMA21 hace 3 ruedas"` si lo relevante es el evento y no el orden.

**limitacion:** "Toda media es rezagada por construcción, y el cruce dorado confirma cuando buena parte del movimiento ya ocurrió. El par rápido corrige ese rezago a cambio de más señales falsas: en mercado lateral la WMA10 cruza la WMA21 varias veces por mes sin que cambie nada. Por eso un cruce rápido aislado no es una señal, solo un aviso para ir a mirar el resto."

**escala:** omitir.

**Cómo leer el cruce rápido sin comerse el ruido.** El bloque `medias_estado` del script trae `cruce_rapido` con el tipo, la fecha, cuántas velas pasaron y la separación porcentual actual entre ambas medias. Tres criterios filtran la mayoría de los falsos positivos: que la separación se esté abriendo en vez de coquetear alrededor de cero, que el ADX no esté bajo 20 (sin tendencia, el cruce no significa nada) y sobre todo que haya confluencia. Un cruce alcista de WMA10 sobre WMA21 con el azul del Koncorde subiendo, el histograma del MACD girando y el RSI recuperando 50 es un cambio de tendencia temprano; el mismo cruce con el azul cayendo es una trampa. Ese cruce de evidencias es lo que decide, no el cruce de las líneas.

---

## ADX (14)

**que_mide:** "Mide la fuerza de la tendencia sin decir en qué dirección va. Sobre 25 indica que hay una tendencia definida y que vale la pena operar a favor de ella; bajo 20 indica mercado lateral, donde las señales de seguimiento de tendencia fallan y conviene operar por rango. La dirección la dan los componentes +DI y -DI."

**Umbrales:** <20 sin tendencia, 20-25 tendencia incipiente, 25-40 tendencia sólida, >40 tendencia muy fuerte (y a menudo madura).

**limitacion:** "Un ADX alto no es alcista ni bajista: una caída violenta también genera ADX alto. Interpretarlo como señal direccional es un error frecuente."

**escala:** `{"min":0,"max":60,"dec":1,"zonas":[{"desde":0,"hasta":20,"color":"bear"},{"desde":20,"hasta":25,"color":"neut"},{"desde":25,"hasta":60,"color":"bull"}]}`

Acá el color no representa dirección sino calidad de la señal: verde significa "hay tendencia que seguir".

---

## Volumen relativo

**que_mide:** "Compara el volumen de las últimas sesiones contra su promedio de 20. El volumen es la única variable que no se puede manipular fácilmente: valida si un movimiento tiene participación real detrás. Una ruptura de resistencia con volumen 50% sobre el promedio es creíble; la misma ruptura con volumen flojo suele ser una trampa."

**Cargá el valor** como múltiplo o porcentaje, por ejemplo `"1,8x prom. 20d"`.

**limitacion:** "Se distorsiona en vencimientos de opciones, rebalanceos de índices y días de resultados. Un pico aislado de volumen no siempre significa convicción."

**escala:** `{"min":0,"max":3,"dec":1,"zonas":[{"desde":0,"hasta":0.8,"color":"bear"},{"desde":0.8,"hasta":1.3,"color":"neut"},{"desde":1.3,"hasta":3,"color":"bull"}]}`

---

## Estocástico (14,3,3)

**que_mide:** "Ubica el cierre actual dentro del rango de máximos y mínimos de las últimas 14 sesiones. Cerca de 100 significa que el precio cierra en la parte alta de su rango reciente, cerca de 0 en la parte baja. Es más rápido y más ruidoso que el RSI, y funciona mejor en mercados laterales que en tendencias."

**Umbrales:** >80 sobrecompra, <20 sobreventa. El cruce de %K sobre %D dentro de esas zonas es la señal.

**limitacion:** "En tendencias sostenidas se satura en los extremos y genera señales contrarias constantes."

**escala:** `{"min":0,"max":100,"dec":0,"zonas":[{"desde":0,"hasta":20,"color":"bull"},{"desde":20,"hasta":80,"color":"neut"},{"desde":80,"hasta":100,"color":"bear"}]}`

---

## ATR (14)

**que_mide:** "Mide el rango promedio que recorre el precio por sesión, incluyendo los gaps. No dice dirección: dice cuánto se mueve el activo. Sirve para dimensionar el stop loss, porque un stop más cerca que 1,5 ATR del precio tiene alta probabilidad de saltar solo por ruido normal."

**Cargá el valor** en unidades de precio y también como porcentaje: `"3,42 (2,1% del precio)"`.

**limitacion:** "Es puramente descriptivo. Un ATR alto no anticipa dirección, solo advierte que el riesgo por unidad es mayor y que hay que reducir el tamaño de la posición."

**escala:** omitir.

---

## Bandas de Bollinger (20,2)

**que_mide:** "Dibuja dos bandas a dos desvíos estándar de la media de 20 sesiones. El precio pasa cerca del 95% del tiempo dentro de ellas. Cuando las bandas se estrechan (squeeze), la volatilidad está comprimida y suele anticipar un movimiento fuerte, aunque no dice hacia dónde. Tocar la banda superior no es señal de venta: en tendencias fuertes el precio camina sobre ella."

**limitacion:** "El estrechamiento anticipa magnitud, no dirección. Operar los toques de banda en contra de la tendencia es una de las formas más rápidas de perder capital."

**escala:** omitir; alternativamente usar %B con escala 0-100.

---

## OBV / acumulación-distribución

**que_mide:** "Acumula el volumen sumándolo en las sesiones alcistas y restándolo en las bajistas. Su utilidad está en las divergencias: si el precio hace máximos crecientes pero el OBV no acompaña, significa que la suba se está haciendo sin participación real y suele preceder una corrección."

**limitacion:** "El nivel absoluto no significa nada; solo importa su pendiente y su divergencia contra el precio."

**escala:** omitir.

---

## Perfil de volumen (Volume Profile)

Este indicador **no va en el array `indicadores`**: tiene su propio bloque `volume_profile` y su propia sección en el informe, con un histograma horizontal y una capa superpuesta sobre el gráfico de precio. Se calcula con `scripts/compute_indicators.py`.

**Qué mide.** Los indicadores clásicos proyectan el volumen sobre el eje del tiempo: cuánto se operó cada día. El perfil lo proyecta sobre el eje del precio: cuánto se operó en cada nivel. El cambio de eje importa porque el mercado no recuerda fechas, recuerda precios. Donde hubo mucho volumen quedaron muchas posiciones abiertas, y esas posiciones se defienden.

**Conceptos y cómo leerlos:**

El **POC** (point of control) es el precio de mayor volumen del período. Funciona como imán: cuando el precio se aleja tiende a volver a testearlo. Un POC que sube período tras período confirma tendencia alcista mejor que muchos osciladores.

La **value area** (VAL a VAH) es el rango que concentra el 70% del volumen. Es donde el mercado considera que el precio es "justo". Dentro de la value area el precio se mueve despacio porque hay oferta y demanda en cada nivel; fuera de ella se mueve rápido. Un precio que sale de la value area y no logra volver en pocas sesiones suele estar iniciando un tramo direccional.

Los **HVN** (high volume nodes) son zonas de alto volumen fuera del POC. Frenan el precio: sirven como objetivos de toma de ganancia y como soportes o resistencias de calidad. Ponerlos en el mismo lugar que un nivel dibujado a mano le da mucha más solidez al nivel.

Los **LVN** (low volume nodes) son huecos donde casi no se operó, típicamente precios que el mercado rechazó rápido. El precio los atraviesa con poca fricción, así que son mal lugar para poner un objetivo y buen lugar para esperar aceleración.

**Cómo usarlo en el plan.** El stop conviene ponerlo del otro lado de un HVN o del VAL, no en medio de un LVN donde el precio pasa sin frenar. Los objetivos conviene ponerlos en el borde cercano de un HVN, no en el centro, porque ahí es donde empieza a aparecer la oferta.

**Limitación.** El perfil depende enteramente de la ventana elegida: 60 velas y 250 velas pueden dar POCs muy distintos y ambos ser correctos para su horizonte. Declará siempre la ventana. Además, un perfil construido desde OHLCV diario reparte el volumen de cada vela a lo largo de su rango, lo que es una aproximación: el perfil real se construye con datos intradiarios y puede diferir en los detalles, aunque el POC y la value area suelen coincidir bien.

---

## Koncorde

Tampoco va en `indicadores`: tiene bloque `koncorde` propio y su subpanel en el informe. Lo calcula `scripts/compute_indicators.py` con la fórmula de Blai5.

**Qué mide.** Intenta responder quién está del otro lado de la operación. Parte de una observación vieja: el dinero institucional prefiere operar cuando el volumen es bajo y nadie mira, porque necesita construir posiciones grandes sin mover el precio en contra; el minorista, en cambio, entra cuando el volumen ya explotó y la noticia está en todos lados. El indicador separa esos dos flujos con dos índices distintos.

**Las cuatro series:**

El **área azul** deriva del NVI (índice de volumen negativo), que solo acumula variación de precio en las sesiones de volumen *menor* al día anterior. Es la mano fuerte. Sobre cero y subiendo significa acumulación; bajo cero y bajando, distribución. Es la serie que hay que mirar primero.

El **área verde** es la tendencia más el oscilador del PVI (índice de volumen positivo), que acumula solo en sesiones de volumen creciente. Es la mano débil, el flujo que persigue el movimiento. Verde muy alto no es buena noticia por sí solo.

El **área marrón** es un compuesto de tendencia: `(RSI + MFI + oscilador de Bollinger + estocástico/3) / 2`. Por construcción vive en una banda positiva, típicamente entre 20 y 100, así que **no tiene sentido leer si "cruza cero"**. Sus referencias son su propia media, su máximo histórico (lo que los usuarios de Blai5 llaman "picos nevados") y su mínimo histórico ("el mar").

La **línea roja** es la EMA de 15 del marrón. El marrón por encima de ella indica tendencia ganando fuerza.

**Las lecturas que importan:**

Azul subiendo con verde plano o cayendo es el patrón de suelo: la mano fuerte compra mientras el minorista está desinteresado. Suele aparecer antes de que el precio confirme nada, y es la razón principal para mirar este indicador.

Verde disparado con azul cayendo es el patrón de techo: el minorista compra el volumen que la mano fuerte está soltando. Si además el precio hace un máximo mayor mientras el azul hace un máximo menor, es divergencia bajista de mano fuerte y merece mención explícita en el informe.

Azul sobre cero y estable, con precio subiendo, es simplemente tendencia sana: la mano fuerte está adentro y no necesita agregar.

**Limitación.** Es un indicador de flujo derivado del precio y el volumen, no una lectura real del libro de órdenes: no ve órdenes institucionales, las infiere. En activos de poco volumen o con muchos huecos de cotización el NVI se vuelve ruidoso y la lectura pierde valor. Necesita al menos unas 130 velas para estabilizarse porque usa ventanas de 90. Y como todo indicador de acumulación, puede señalar acumulación durante meses antes de que el precio reaccione: sirve para el sesgo, no para el timing.

---

## Cómo elegir cuáles incluir

Cinco a siete indicadores es el rango útil. Menos deja el análisis flaco; más genera redundancia (RSI y estocástico miden casi lo mismo) y le da al lector una falsa sensación de confirmación múltiple cuando en realidad está mirando el mismo dato tres veces.

Una combinación que cubre bien los ángulos: uno de tendencia (medias), uno de momentum (RSI), uno de confirmación de momentum (MACD), uno de fuerza de tendencia (ADX), uno de participación (volumen relativo) y uno de volatilidad (ATR) cuando el stop necesita justificación.

El perfil de volumen y el Koncorde quedan fuera de esa cuenta: van en sus propios bloques y no compiten por el cupo del array. Sí conviene que la lectura de ambos aparezca reflejada en la `nota` del componente Volumen del scoring y, si es determinante, en la tesis del resumen.

Si dos indicadores se contradicen, no lo escondas: esa contradicción es información valiosa y debería reflejarse bajando la confianza declarada en el resumen.
