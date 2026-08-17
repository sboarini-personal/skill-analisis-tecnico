#!/usr/bin/env python3
"""
Renderiza un informe de analisis tecnico interactivo (HTML autocontenido)
a partir de un JSON de analisis.

Uso:
    python3 build_report.py analisis.json informe_TICKER.html

Que hace ademas de inyectar los datos:
  - Valida que existan los bloques minimos y avisa por stderr si falta algo.
  - Calcula valores derivados si no vinieron dados: riesgo_pct, rr_tp1, rr_tp2,
    retorno_pct de cada escenario, y el score total a partir de `scoring`.
  - Verifica coherencia del plan (SL/TP del lado correcto segun el sesgo,
    probabilidades que suman 100, score consistente con el sesgo declarado).
    Los problemas se reportan como WARN; no bloquean la generacion.

El HTML resultante no depende de red: todo el CSS/JS/SVG va inline.
"""

import json
import sys
import os

def _buscar_template():
    """Ubica report_template.html en los dos layouts posibles.

    En el arbol de desarrollo el template vive en ../assets/. En la skill ya
    instalada vive al lado de este script, porque el paquete se aplana: esta
    app no conserva subcarpetas al instalar una skill. Buscar en ambos lugares
    evita tener que reescribir este archivo al empaquetar.
    """
    d = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(d, "report_template.html"),                 # paquete aplanado
        os.path.join(d, "..", "assets", "report_template.html"),  # arbol de desarrollo
        os.path.join(d, "assets", "report_template.html"),
    ]
    for c in candidatos:
        if os.path.isfile(c):
            return os.path.abspath(c)
    return None


TEMPLATE = _buscar_template()
_TEMPLATE_BUSCADO = [
    "report_template.html (al lado del script)",
    "../assets/report_template.html",
    "assets/report_template.html",
]

WARN = []


def w(msg):
    WARN.append(msg)


def num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def derive(d):
    meta = d.setdefault("meta", {})
    res = d.setdefault("resumen", {})

    # --- score total desde el desglose ---
    scoring = d.get("scoring") or []
    if scoring:
        total = sum(num(k.get("puntaje")) or 0 for k in scoring)
        peso = sum(num(k.get("peso")) or 0 for k in scoring)
        if abs(peso - 100) > 0.01:
            w(f"Los pesos del scoring suman {peso:g}, no 100.")
        if res.get("score") is None:
            res["score"] = round(total)
        elif abs(num(res["score"]) - total) > 0.51:
            w(f"resumen.score={res['score']} pero el desglose suma {total:g}. "
              f"Se usa el desglose.")
            res["score"] = round(total)

    score = num(res.get("score"))
    sesgo = (res.get("sesgo") or "").lower()
    if score is not None:
        if score >= 60 and sesgo.startswith("baj"):
            w(f"Score {score:g} (alto) con sesgo Bajista: revisar coherencia.")
        if score <= 40 and sesgo.startswith("alc"):
            w(f"Score {score:g} (bajo) con sesgo Alcista: revisar coherencia.")

    # --- gestion de riesgo ---
    g = d.get("gestion_riesgo")
    if g:
        e, sl = num(g.get("entrada")), num(g.get("stop_loss"))
        t1, t2 = num(g.get("tp1")), num(g.get("tp2"))
        if e and sl:
            riesgo = abs(e - sl)
            if g.get("riesgo_pct") is None:
                g["riesgo_pct"] = round(riesgo / e * 100, 2)
            if riesgo == 0:
                w("Entrada y stop loss son iguales: R/R indefinido.")
            else:
                if t1 is not None and g.get("rr_tp1") is None:
                    g["rr_tp1"] = round(abs(t1 - e) / riesgo, 2)
                if t2 is not None and g.get("rr_tp2") is None:
                    g["rr_tp2"] = round(abs(t2 - e) / riesgo, 2)
            is_long = not sesgo.startswith("baj")
            if is_long:
                if sl >= e:
                    w("Operativa alcista pero el stop loss esta por encima de la entrada.")
                if t1 is not None and t1 <= e:
                    w("Operativa alcista pero TP1 esta por debajo de la entrada.")
                if t1 is not None and t2 is not None and t2 <= t1:
                    w("TP2 no supera a TP1.")
            else:
                if sl <= e:
                    w("Operativa bajista pero el stop loss esta por debajo de la entrada.")
                if t1 is not None and t1 >= e:
                    w("Operativa bajista pero TP1 esta por encima de la entrada.")
        rr2 = num(g.get("rr_tp2")) or num(g.get("rr_tp1"))
        if rr2 is not None and rr2 < 1.5:
            w(f"R/R de {rr2:g} es pobre (<1.5). Justificar o replantear los niveles.")
        if not g.get("invalidacion"):
            w("Falta gestion_riesgo.invalidacion: el lector no sabe cuando abandonar la tesis.")

    # --- escenarios ---
    sc = d.get("escenarios") or []
    if sc:
        tot = sum(num(x.get("probabilidad")) or 0 for x in sc)
        if abs(tot - 100) > 0.5:
            w(f"Las probabilidades de los escenarios suman {tot:g}%, no 100%.")
        base = None
        if d.get("gestion_riesgo"):
            base = num(d["gestion_riesgo"].get("entrada"))
        base = base or num(meta.get("precio_actual"))
        for x in sc:
            if x.get("retorno_pct") is None and base and num(x.get("objetivo")) is not None:
                x["retorno_pct"] = round((num(x["objetivo"]) - base) / base * 100, 2)

    # --- serie de precios ---
    ps = d.get("precio_serie")
    if ps:
        f = ps.get("fechas") or []
        for key in ("cierres", "volumen"):
            if ps.get(key) and len(ps[key]) != len(f):
                w(f"precio_serie.{key} tiene {len(ps[key])} valores y hay {len(f)} fechas.")
        if ps.get("ohlc") and len(ps["ohlc"]) != len(f):
            w(f"precio_serie.ohlc tiene {len(ps['ohlc'])} velas y hay {len(f)} fechas.")
        for nm, arr in (ps.get("medias") or {}).items():
            if len(arr) != len(f):
                w(f"precio_serie.medias['{nm}'] tiene {len(arr)} valores y hay {len(f)} fechas.")
        if len(f) < 30:
            w(f"Solo {len(f)} velas en la serie: el grafico va a quedar pobre. "
              f"Apuntar a 90-250.")
    else:
        w("Sin precio_serie: el informe se genera pero sin grafico de precio.")

    # --- perfil de volumen ---
    vp = d.get("volume_profile")
    if vp:
        bins = vp.get("bins") or []
        if len(bins) < 8:
            w(f"volume_profile tiene {len(bins)} rangos: con menos de ~12 el perfil "
              f"no distingue nada. Regenerar con compute_indicators.py.")
        poc, val, vah = num(vp.get("poc")), num(vp.get("val")), num(vp.get("vah"))
        if None in (poc, val, vah):
            w("volume_profile sin poc / val / vah: el grafico pierde sus referencias.")
        elif not (val <= poc <= vah):
            w(f"El POC ({poc:g}) cae fuera de la value area {val:g}-{vah:g}: "
              f"imposible por construccion, revisar la fuente del bloque.")
        if bins and poc is not None:
            if not any(b.get("es_poc") for b in bins):
                w("Ningun bin marcado con es_poc: el grafico no va a resaltar el POC.")
        pa = num(meta.get("precio_actual"))
        if pa is not None and bins:
            top = num(bins[-1].get("hasta"))
            bot = num(bins[0].get("desde"))
            if top is not None and bot is not None and not (bot <= pa <= top):
                w(f"El precio actual ({pa:g}) queda fuera del rango del perfil "
                  f"({bot:g}-{top:g}): el perfil esta desactualizado.")
    else:
        w("Sin volume_profile: se pierde la lectura de donde se acumulo el volumen. "
          "Generalo con compute_indicators.py.")

    # --- koncorde ---
    kc = d.get("koncorde")
    if kc:
        nf = len(kc.get("fechas") or [])
        if nf < 40:
            w(f"koncorde con {nf} puntos: hacen falta ~60-120 para leer las fases.")
        for s in ("verde", "marron", "azul", "media"):
            arr = kc.get(s)
            if arr is None:
                w(f"koncorde.{s} ausente.")
            elif len(arr) != nf:
                w(f"koncorde.{s} tiene {len(arr)} valores y hay {nf} fechas.")
        est = (kc.get("estado") or "").lower()
        az = num(kc.get("azul_actual"))
        if az is not None:
            if est.startswith("acum") and az < 0:
                w(f"koncorde.estado='Acumulacion' pero azul_actual={az:g} (<0): "
                  f"la mano fuerte esta fuera. Revisar la lectura.")
            if est.startswith("distrib") and az > 0:
                w(f"koncorde.estado='Distribucion' pero azul_actual={az:g} (>0).")
        if not kc.get("lectura"):
            w("Falta koncorde.lectura: el grafico queda sin interpretacion del caso.")
    else:
        w("Sin koncorde: no hay lectura de acumulacion/distribucion de mano fuerte. "
          "Generalo con compute_indicators.py.")

    # --- minimos de contenido ---
    if len(d.get("indicadores") or []) < 4:
        w("Menos de 4 indicadores: el analisis queda flaco.")
    nv = d.get("niveles") or {}
    if not nv.get("soportes") or not nv.get("resistencias"):
        w("Faltan soportes o resistencias.")
    if not d.get("fundamental"):
        w("Sin bloque fundamental (P/E actual y forward).")
    for campo in ("tesis",):
        if not res.get(campo):
            w(f"Falta resumen.{campo}.")
    if not d.get("conclusion"):
        w("Falta conclusion.")
    return d


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        print("ERROR: el JSON raiz debe ser un objeto con las claves meta, resumen, etc.",
              file=sys.stderr)
        sys.exit(2)
    data = derive(data)

    if TEMPLATE is None:
        print("ERROR: no encuentro report_template.html. Busque en:", file=sys.stderr)
        for c in _TEMPLATE_BUSCADO:
            print(f"  - {c}", file=sys.stderr)
        print("El template tiene que estar al lado de este script o en ../assets/.",
              file=sys.stderr)
        sys.exit(2)

    with open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()

    payload = json.dumps(data, ensure_ascii=False)
    # evita que un </script> dentro de un texto rompa el documento
    payload = payload.replace("</", "<\\/")
    if "/*__DATA__*/null" not in html:
        print("ERROR: el template no contiene el marcador /*__DATA__*/null", file=sys.stderr)
        sys.exit(2)
    html = html.replace("/*__DATA__*/null", payload)

    meta = data.get("meta", {})
    titulo = f"{meta.get('ticker','')} · Análisis técnico · {meta.get('fecha_analisis','')}".strip(" ·")
    html = html.replace("__TITLE__", titulo or "Análisis técnico")

    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(html)

    kb = os.path.getsize(dst) / 1024
    print(f"OK: {dst} ({kb:.0f} KB)")
    if WARN:
        print(f"\n{len(WARN)} advertencia(s) — revisalas antes de entregar:", file=sys.stderr)
        for m in WARN:
            print(f"  WARN: {m}", file=sys.stderr)


if __name__ == "__main__":
    main()
