#!/usr/bin/env python3
"""
Suite de verificacion de la skill.

    python3 tests/run_all.py

Que verifica, en orden:

1. compute_indicators.py corre sobre la serie de ejemplo y produce numeros
   reproducibles (mismo POC y mismo Koncorde que el ejemplo guardado).
2. build_report.py renderiza el informe completo sin advertencias.
3. Las cuatro variantes de datos (ambos bloques de volumen, solo perfil, solo
   Koncorde, ninguno) renderizan y degradan bien: la seccion que no tiene datos
   se oculta en lugar de romperse.
4. Un JSON deliberadamente incoherente dispara las validaciones que corresponden.
5. El JavaScript del informe se ejecuta sin errores en un DOM simulado y no
   filtra NaN ni undefined a la pantalla. Se ejercitan los toggles de capas (dos
   pasadas: apagar todo y volver a prender), el simulador de precio en sus
   extremos y todos los tooltips.

Los pasos 5 necesitan Node. Si no esta instalado se saltean con aviso en lugar de
fallar, porque el resto de la suite sigue siendo util.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

TESTS = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTS)
SKILL = os.path.join(RAIZ, "analisis-tecnico-boa")
EJEMPLOS = os.path.join(RAIZ, "examples")
COMPUTE = os.path.join(SKILL, "scripts", "compute_indicators.py")
BUILD = os.path.join(SKILL, "scripts", "build_report.py")

OK, FALLOS, SALTEADOS = [], [], []


def paso(nombre, cond, detalle=""):
    (OK if cond else FALLOS).append(nombre)
    print(f"  {'OK  ' if cond else 'FALLA'}  {nombre}" + (f"  -- {detalle}" if detalle else ""))
    return cond


def correr(cmd):
    r = subprocess.run([sys.executable] + cmd if cmd[0].endswith(".py") else cmd,
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="skilltest_")
    node = shutil.which("node")
    try:
        # ---------------------------------------------------------- 1. calculo
        print("\n[1] Calculo de indicadores")
        calc = os.path.join(tmp, "calc.json")
        rc, out, err = correr([COMPUTE, os.path.join(EJEMPLOS, "serie_nvda.json"),
                               calc, "--vp-ventana", "90"])
        if not paso("compute_indicators.py corre sin error", rc == 0, err.strip()[:200]):
            print(err)
            return resumen()
        c = json.load(open(calc, encoding="utf-8"))
        ref = json.load(open(os.path.join(EJEMPLOS, "demo_final.json"), encoding="utf-8"))

        paso("perfil de volumen reproducible (mismo POC)",
             c["volume_profile"]["poc"] == ref["volume_profile"]["poc"],
             f'{c["volume_profile"]["poc"]} vs {ref["volume_profile"]["poc"]}')
        paso("POC dentro de la value area",
             c["volume_profile"]["val"] <= c["volume_profile"]["poc"] <= c["volume_profile"]["vah"])
        paso("value area cubre al menos el 70% del volumen",
             c["volume_profile"]["pct_en_value_area"] >= 70)
        bins = c["volume_profile"]["bins"]
        paso("exactamente un bin marcado como POC",
             sum(1 for b in bins if b["es_poc"]) == 1)
        paso("Koncorde reproducible (ultimos 5 valores del azul)",
             c["koncorde"]["azul"][-5:] == ref["koncorde"]["azul"][-5:])
        k = c["koncorde"]
        paso("series de Koncorde alineadas con sus fechas",
             all(len(k[s]) == len(k["fechas"]) for s in ("verde", "marron", "azul", "media")))
        paso("marron vive en banda positiva (no cruza cero por construccion)",
             min(v for v in k["marron"] if v is not None) > -50)

        # -------------------------------------------------------- 1b. medias
        print("\n[1b] Medias moviles")
        med, me = c["precio_serie"]["medias"], c["medias_estado"]
        paso("el set es exactamente WMA10, WMA21, EMA50, SMA200",
             list(med.keys()) == ["WMA10", "WMA21", "EMA50", "SMA200"],
             str(list(med.keys())))
        n_velas = len(json.load(open(os.path.join(EJEMPLOS, "serie_nvda.json"),
                                     encoding="utf-8"))["fechas"])
        paso("todas las series tienen el largo de la serie de precios",
             all(len(v) == n_velas for v in med.values()))
        paso("cada media arranca en su periodo (N-1 nulos al principio)",
             all(sum(1 for x in med[nm] if x is None) == min(per - 1, n_velas)
                 for nm, per in (("WMA10", 10), ("WMA21", 21),
                                 ("EMA50", 50), ("SMA200", 200))))

        # Importado para probar las primitivas de media una por una. Sin bytecode:
        # un __pycache__ dentro de scripts/ ensucia el arbol que copia el instalador.
        sys.dont_write_bytecode = True
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import compute_indicators as ci

        rampa = [float(i) for i in range(60)]
        paso("WMA tiene menos rezago que SMA del mismo largo (rampa lineal)",
             ci.sma(rampa, 10)[-1] < ci.wma(rampa, 10)[-1] < rampa[-1])
        paso("WMA de una serie constante devuelve la constante",
             abs(ci.wma([42.0] * 40, 21)[-1] - 42.0) < 1e-12)
        ref_wma = [sum(rampa[i - 9 + j] * (j + 1) for j in range(10)) / 55.0
                   for i in range(9, len(rampa))]
        paso("WMA coincide con la ponderacion lineal calculada aparte",
             all(abs(a - b) < 1e-9
                 for a, b in zip([x for x in ci.wma(rampa, 10) if x is not None], ref_wma)))

        paso("medias_estado declara SMA200 sin dato con serie de 150 velas",
             me["sin_dato"] == ["SMA200"] and me["alineacion"].endswith("_parcial"),
             f'sin_dato={me["sin_dato"]} alineacion={me["alineacion"]}')
        paso("el orden del abanico coincide con los valores reales",
             me["orden"] == " > ".join(
                 ["P" if nm == "Precio" else nm for nm, _ in sorted(
                     [(nm, v) for nm, v in me["actuales"].items() if v is not None]
                     + [("Precio", c["ultimo"]["close"])], key=lambda t: -t[1])]),
             me["orden"])

        cr = me["cruce_rapido"]
        w10 = [x for x in med["WMA10"]]
        w21 = [x for x in med["WMA21"]]
        cruces = [i for i in range(1, n_velas)
                  if None not in (w10[i - 1], w21[i - 1], w10[i], w21[i])
                  and ((w10[i - 1] <= w21[i - 1] and w10[i] > w21[i])
                       or (w10[i - 1] >= w21[i - 1] and w10[i] < w21[i]))]
        paso("cruce_rapido apunta al ultimo cruce real de las series",
             bool(cr) == bool(cruces)
             and (not cruces or cr["velas_desde"] == n_velas - 1 - cruces[-1]),
             str(cr))
        paso("el tipo del cruce coincide con la posicion posterior de las medias",
             not cr or (cr["tipo"] == "alcista") == (w10[-1] > w21[-1]))

        # ------------------------------------ 1c. calculo vs grafico (SMA200)
        print("\n[1c] Ventana de calculo separada de la ventana de grafico")
        N = 460
        largo = {"fechas": [f"20{24 + i // 336:02d}-{1 + (i // 28) % 12:02d}-{1 + i % 28:02d}"
                            for i in range(N)],
                 "ohlc": [[100 + i * .5, 101 + i * .5, 99 + i * .5, 100.5 + i * .5]
                          for i in range(N)],
                 "volumen": [1_000_000 + (i % 7) * 50_000 for i in range(N)]}
        src = os.path.join(tmp, "serie_larga.json")
        dst = os.path.join(tmp, "calc_largo.json")
        json.dump(largo, open(src, "w", encoding="utf-8"))
        rc2, _, err2 = correr([COMPUTE, src, dst, "--velas-grafico", "250"])
        cl = json.load(open(dst, encoding="utf-8")) if rc2 == 0 else {}
        paso("con 460 velas la SMA200 se calcula y el abanico queda completo",
             rc2 == 0 and cl["ultimo"]["sma200"] is not None
             and cl["medias_estado"]["sin_dato"] == []
             and cl["medias_estado"]["alineacion"] == "alcista_completa",
             str(cl.get("medias_estado", {}).get("alineacion")))
        paso("en tendencia alcista limpia no hay cruces espurios del par rapido",
             rc2 == 0 and cl["medias_estado"]["cruce_rapido"] is None)

        psl = cl["precio_serie"]
        paso("precio_serie sale recortado a --velas-grafico",
             len(psl["fechas"]) == 250 and len(psl["ohlc"]) == 250
             and len(psl["volumen"]) == 250,
             f'{len(psl["fechas"])} velas')
        paso("las medias recortadas siguen alineadas con las fechas",
             all(len(v) == 250 for v in psl["medias"].values()))
        paso("460 de calculo alcanzan para dibujar la SMA200 en todo el grafico",
             all(v is not None for v in psl["medias"]["SMA200"]))
        paso("el recorte no altera el calculo (la cola coincide con la serie completa)",
             psl["fechas"] == largo["fechas"][-250:]
             and psl["ohlc"] == largo["ohlc"][-250:])
        paso("medias_estado reporta las velas realmente calculadas, no las dibujadas",
             cl["medias_estado"]["velas_calculadas"] == N)

        rc3, _, err3 = correr([COMPUTE, src, os.path.join(tmp, "c_todo.json"),
                               "--velas-grafico", "0"])
        ct = json.load(open(os.path.join(tmp, "c_todo.json"), encoding="utf-8"))
        paso("--velas-grafico 0 devuelve la serie entera",
             len(ct["precio_serie"]["fechas"]) == N)
        paso("recortar no cambia ningun indicador del ultimo cierre",
             ct["ultimo"] == cl["ultimo"])

        corta = {k: v[:190] for k, v in largo.items()}
        json.dump(corta, open(os.path.join(tmp, "corta.json"), "w", encoding="utf-8"))
        _, _, err4 = correr([COMPUTE, os.path.join(tmp, "corta.json"),
                             os.path.join(tmp, "c_corta.json")])
        paso("con serie corta el aviso dice cuantas velas faltan para la SMA200",
             "Descarga 10 velas mas" in err4, err4.strip().splitlines()[0][:120])

        # ------------------------------------------------------- 2/3. render
        print("\n[2] Render y degradacion")
        base = json.load(open(os.path.join(EJEMPLOS, "demo_final.json"), encoding="utf-8"))
        variantes = {"completo": base}
        v = json.loads(json.dumps(base)); v.pop("koncorde"); variantes["solo_perfil"] = v
        v = json.loads(json.dumps(base)); v.pop("volume_profile"); variantes["solo_koncorde"] = v
        v = json.loads(json.dumps(base)); v.pop("volume_profile"); v.pop("koncorde")
        variantes["sin_volumen_institucional"] = v

        htmls = {}
        for nombre, datos in variantes.items():
            src = os.path.join(tmp, nombre + ".json")
            dst = os.path.join(tmp, nombre + ".html")
            json.dump(datos, open(src, "w", encoding="utf-8"), ensure_ascii=False)
            rc, out, err = correr([BUILD, src, dst])
            warns = [l for l in err.splitlines() if "WARN" in l]
            esperadas = 0 if nombre == "completo" else (1 if "solo_" in nombre else 2)
            paso(f"{nombre}: renderiza", rc == 0 and os.path.exists(dst))
            paso(f"{nombre}: {len(warns)} advertencia(s), esperadas {esperadas}",
                 len(warns) == esperadas, "; ".join(w.strip()[:90] for w in warns))
            htmls[nombre] = dst

        # El demo tiene 150 velas y por eso no llega a la SMA200. Este caso
        # renderiza el abanico completo para confirmar que la cuarta linea se
        # dibuja y entra en la leyenda: la paleta del template tiene 4 colores
        # justos y una quinta media se solaparia sin aviso.
        cuatro = json.loads(json.dumps(base))
        cuatro["precio_serie"] = psl
        cuatro["meta"]["precio_actual"] = psl["ohlc"][-1][3]
        cuatro.pop("volume_profile"); cuatro.pop("koncorde")
        for lado, factor in (("soportes", .97), ("resistencias", 1.03)):
            for niv in cuatro["niveles"][lado]:
                niv["precio"] = round(psl["ohlc"][-1][3] * factor, 2)
        src = os.path.join(tmp, "cuatro_medias.json")
        dst = os.path.join(tmp, "cuatro_medias.html")
        json.dump(cuatro, open(src, "w", encoding="utf-8"), ensure_ascii=False)
        rc, out, err = correr([BUILD, src, dst])
        html = open(dst, encoding="utf-8").read() if rc == 0 else ""
        paso("abanico completo: renderiza con las cuatro medias",
             rc == 0 and all(f'"{nm}"' in html
                             for nm in ("WMA10", "WMA21", "EMA50", "SMA200")))
        htmls["cuatro_medias"] = dst

        # -------------------------------------------------- 4. validaciones
        print("\n[3] Validaciones sobre datos incoherentes")
        roto = json.loads(json.dumps(base))
        roto["volume_profile"]["poc"] = 9999
        roto["meta"]["precio_actual"] = 9999
        roto["koncorde"]["estado"] = "Acumulacion"
        roto["koncorde"]["azul_actual"] = -40
        src = os.path.join(tmp, "roto.json")
        json.dump(roto, open(src, "w", encoding="utf-8"), ensure_ascii=False)
        rc, out, err = correr([BUILD, src, os.path.join(tmp, "roto.html")])
        for frag, desc in [("POC", "detecta POC fuera de la value area"),
                           ("fuera del rango del perfil", "detecta precio fuera del perfil"),
                           ("azul_actual", "detecta estado de Koncorde incoherente")]:
            paso(desc, frag in err)

        # ------------------------------------------------------ 5. JavaScript
        print("\n[4] Ejecucion del JavaScript del informe")
        if not node:
            SALTEADOS.append("verificacion de JavaScript (Node no encontrado)")
            print("  SALTEADO  Node no esta instalado; se omite la verificacion del JS")
        else:
            for nombre, ruta in htmls.items():
                for script in ("check.js", "interact.js"):
                    r = subprocess.run([node, os.path.join(TESTS, script), ruta],
                                       capture_output=True, text=True, cwd=TESTS)
                    salida = r.stdout.strip()
                    limpio = r.returncode == 0 and "anomalias:0" in salida and "❌" not in salida
                    paso(f"{nombre} / {script}", limpio,
                         salida.replace("\n", " | ")[:150] if not limpio else "")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return resumen()


def resumen():
    print("\n" + "=" * 62)
    print(f"{len(OK)} verificaciones OK, {len(FALLOS)} fallas, {len(SALTEADOS)} salteadas")
    for f in FALLOS:
        print(f"  FALLA: {f}")
    for s in SALTEADOS:
        print(f"  SALTEADO: {s}")
    print("=" * 62)
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
