# Skill: Análisis Técnico BOA

Proyecto de desarrollo de la skill `analisis-tecnico-boa`, que genera informes de análisis técnico bursátil como archivos HTML autocontenidos e interactivos.

## Estructura

```
Skill Analisis Tecnico/
├── README.md                        este archivo
├── build.py                         prepara la skill para instalar y la verifica
├── analisis-tecnico-boa/            LA SKILL — árbol fuente
│   ├── SKILL.md                     instrucciones + frontmatter YAML
│   ├── scripts/
│   │   ├── compute_indicators.py    calcula indicadores desde el OHLCV
│   │   └── build_report.py          renderiza el HTML + valida el JSON
│   ├── assets/
│   │   └── report_template.html     el informe completo, CSS/JS/SVG inline
│   └── references/
│       ├── schema.md                contrato de datos campo por campo
│       ├── scoring.md               rúbrica del score técnico 0-100
│       └── indicadores.md           qué mide cada indicador y cuándo miente
├── instalar-skills/                 lo que se copia a la app
│   └── analisis-tecnico-boa/        copia generada desde el árbol fuente
├── examples/
│   ├── serie_nvda.json              serie OHLCV de entrada
│   ├── demo_final.json              análisis completo de ejemplo
│   └── informe_NVDA_demo.html       el informe renderizado
└── tests/
    ├── run_all.py                   suite completa de verificación
    ├── domshim.js                   DOM simulado para Node
    ├── check.js                     ejecuta el JS del informe y busca fugas
    └── interact.js                  ejercita toggles, simulador y tooltips
```

Se edita `analisis-tecnico-boa/`; `instalar-skills/analisis-tecnico-boa/` es una copia generada, no se toca a mano. El resto es andamiaje de desarrollo.

## Ciclo de trabajo

Editar lo que corresponda dentro de `analisis-tecnico-boa/`, después:

```
python3 tests/run_all.py     # 27 verificaciones, tiene que dar 0 fallas
python3 build.py             # sincroniza el staging y lo verifica ejecutándolo
```

Para que la app tome los cambios hay que cerrarla, copiar el staging al directorio de skills de la app y volver a abrirla. De eso se ocupa el proyecto vecino **Instalador de Skills**, que tiene el script y la explicación completa del porqué:

```
cd "C:\Users\sboar\OneDrive - AMX Argentina S.A\Personal Docs\Claude\Projects\Instalador de Skills"
powershell -ExecutionPolicy Bypass -File .\instalar-skills.ps1 -Origen "C:\Users\sboar\OneDrive - AMX Argentina S.A\Personal Docs\Claude\Projects\Skill Analisis Tecnico\instalar-skills"
```

Y para confirmar después que quedó sana, sin copiar nada:

```
powershell -ExecutionPolicy Bypass -File .\instalar-skills.ps1 -Revisar
```

Ese mismo instalador sirve para cualquier otra skill —propia, oficial o de terceros— y guarda una copia completa de las once oficiales. El motivo por el que hace falta está resumido más abajo y desarrollado en su README.

## Qué verifica la suite de tests

Correr los tests después de tocar el template no es opcional: el informe es un documento con unas 700 líneas de JavaScript y un error de runtime deja secciones vacías sin que nada avise.

La suite cubre cuatro frentes. Primero, que los indicadores sean **reproducibles**: el POC del perfil de volumen y las series del Koncorde tienen que dar exactamente lo mismo que el ejemplo guardado, y se chequean invariantes que deberían cumplirse siempre (el POC cae dentro de la value area, hay exactamente un bin marcado como POC, las series del Koncorde están alineadas con sus fechas).

Segundo, la **degradación**: se renderizan cuatro variantes de datos — con ambos bloques de volumen institucional, con uno solo, con el otro solo, y sin ninguno — y se verifica que las secciones sin datos se oculten en lugar de romperse, y que el script emita exactamente las advertencias esperadas en cada caso.

Tercero, que las **validaciones** disparen: se alimenta un JSON deliberadamente incoherente (POC fuera de la value area, precio fuera del rango del perfil, estado de Koncorde contradiciendo el signo del azul) y se confirma que cada problema sea reportado.

Cuarto, la **ejecución real del JavaScript** contra un DOM simulado en Node. Se ejercitan los toggles de capas en dos pasadas —apagando todas las series y volviéndolas a prender, que es donde aparecen los `Math.max()` sobre arrays vacíos—, el simulador de precio en sus valores extremos y todos los tooltips del documento. Cualquier `NaN` o `undefined` que llegue al HTML o a un atributo SVG se cuenta como anomalía y hace fallar el test. Este control ya atrapó dos bugs reales que no se veían a simple vista.

Si Node no está instalado, ese cuarto bloque se saltea con aviso en lugar de fallar.

## Notas de implementación que conviene no perder

**El frontmatter de `SKILL.md` es frágil por fuera de este repo.** El cargador rechaza el paquete con `SKILL.md frontmatter missing name or description` si el archivo llega con BOM, con saltos CRLF raros o con caracteres que se rompieron en un round-trip por Windows u OneDrive. Por eso `name` y `description` se mantienen en ASCII puro y la descripción va entre comillas dobles. `build.py` normaliza y verifica esto antes de comprimir, y aborta si algo no cierra.

**El importador de `.skill` no instala un paquete: instala un documento.** Es la limitación más cara del proyecto y costó una skill rota en silencio durante varias versiones. Al arrastrar un `.skill`, la app toma `SKILL.md`, le parsea el frontmatter para sacar `name` y `description`, guarda el cuerpo como instrucciones y **descarta todo el resto del zip**. No hay ningún paso que copie `scripts/`, `assets/` ni `references/`. El síntoma es traicionero: la skill se instala sin error, se dispara bien, y el modelo lee instrucciones que mandan a ejecutar scripts que no existen. Como no puede, improvisa los indicadores. Es decir, produce exactamente el informe con números inventados que toda la arquitectura busca evitar.

Esto se comprobó, no se supone: las 19 skills instaladas por esta vía tienen exactamente un archivo cada una, verificado sobre el filesystem. No es profundidad de subcarpetas —un paquete completamente plano se perdió igual, y esa fue una hipótesis previa que resultó falsa—. No es un filtro por extensión, porque las skills que vienen con la app conservan sus `.txt` y `.md`. No es materialización perezosa, porque invocar una skill no crea ningún archivo. Y el manifiesto de skills guarda solo metadata (`skillId`, `name`, `description`, `creatorType`, `updatedAt`, `enabled`) sin un solo campo que apunte a un archivo o a un paquete, que es justamente lo que existiría si preservara bundles. Ningún reempaquetado del `.skill` va a arreglarlo.

**El runtime, en cambio, lee la carpeta de la skill tal cual está en disco.** Ahí no hay ninguna limitación: dos de las skills que vienen incluidas con la app conservan varios archivos —`frontend-design` tiene su `LICENSE.txt` y `pdf-reading` tiene además `REFERENCE.md`—, sin ningún manifiesto de por medio. El formato soporta múltiples archivos de sobra; el único que los tira es el importador. Así que alcanza con copiar la carpeta al directorio de skills de la app, que es persistente y a nivel de cuenta, bajo `%LOCALAPPDATA%\Claude-3p\local-agent-mode-sessions\skills-plugin\…\skills`. De eso se ocupa el proyecto **Instalador de Skills**. Verificado end-to-end: los scripts corren desde la skill ya instalada y generan el informe completo.

**Los *skills directories* de Claude Code no aplican acá.** Se probó armar la skill como plugin `@skills-dir` con su `.claude-plugin/plugin.json` y dejarla en `<proyecto>\.claude\skills\`: la app la ignoró por completo, no apareció el diálogo de confianza del workspace y no cargó nada. Esta app no escanea esas carpetas; usa únicamente su propio directorio en `AppData`. No perder tiempo por ese lado.

Queda un riesgo asumido: si la app hiciera un sync de skills podría pisar lo copiado. Se notaría enseguida —las skills volverían a improvisar— y el respaldo que deja el instalador permite revertir.

**Lo que se instala tiene que ser lo que se verifica.** La versión anterior de `build.py` validaba un zip desempaquetado en un temporal, que no era lo que la app instalaba: daba verde con la skill rota. Ahora `build.py` sincroniza el árbol en `instalar-skills/analisis-tecnico-boa/` y **ejecuta los dos scripts desde ahí** generando un informe real, comprobando de paso que pese lo que tiene que pesar y que el marcador de datos haya quedado reemplazado. Es exactamente el árbol que el instalador copia, así que si el layout se rompió, falla ahí.

**Los mounts de OneDrive y del sandbox no permiten `unlink`.** `rm`, `shutil.rmtree` y `git clone` fallan con `Operation not permitted`. Por eso `sincronizar()` sobreescribe en el lugar en vez de borrar y recrear, y reporta los huérfanos que no pudo borrar en vez de abortar; y por eso cualquier clon de un repo va a `/tmp`.

**No subir el `.md` suelto.** La skill depende del template y de los dos scripts; sin ellos no produce nada.

**El Koncorde está implementado según el código de dos ports publicados en Pine Script**, no de memoria. Un detalle que cuesta caro si se pierde: el port v5 tiene el comentario de cabecera invertido respecto de su propio código. Vale el código, que coincide con la v4 y con la lógica original de Blai5: el **área azul es el NVI y representa la mano fuerte** (que opera en sesiones de volumen bajo, cuando nadie mira), y el **área verde deriva del PVI y representa la mano débil**. El área marrón no está centrada en cero por construcción, así que no tiene sentido leer si "cruza el cero"; sus referencias son su propia media y sus extremos históricos.

**El perfil de volumen se construye desde OHLCV diario**, repartiendo el volumen de cada vela a lo largo de su recorrido. Es una aproximación: el perfil real se arma con datos intradiarios. El POC y la value area suelen coincidir bien igual, pero conviene tenerlo presente antes de discutir diferencias de detalle contra TradingView.

**El cálculo va en el script, no en el prompt.** El Koncorde encadena PVI, NVI, MFI, RSI, oscilador de Bollinger y estocástico sobre ventanas de 90 velas. Pedirle al modelo que lo estime produce números con apariencia de precisión y sin ninguna. Lo mismo vale para el POC. Si alguna vez el informe empieza a salir con indicadores inventados, el problema casi seguro es que el modelo no está corriendo `compute_indicators.py`.
