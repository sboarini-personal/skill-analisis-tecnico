#!/usr/bin/env python3
"""
Calcula todos los indicadores tecnicos del informe a partir de la serie OHLCV.

Uso:
    python3 compute_indicators.py serie.json calculado.json [opciones]

Entrada: un JSON con {"fechas":[...], "ohlc":[[o,h,l,c],...], "volumen":[...]}
o directamente un analisis.json que contenga ese bloque en "precio_serie".

Salida: un JSON con
    ultimo            -> valores del ultimo cierre (RSI, MACD, ADX, ATR, vol rel, etc.)
    precio_serie      -> bloque completo listo para pegar en analisis.json: fechas,
                         ohlc, volumen y las cuatro medias, ya recortado a las
                         velas que se dibujan
    medias_estado     -> lectura del abanico: orden, alineacion, distancias,
                         pendientes y los dos cruces (rapido y estructural)
    volume_profile    -> perfil de volumen por rango de precio, con POC y value area
    koncorde          -> series verde / marron / azul / media del indicador de Blai5

Opciones:
    --vp-bins N       cantidad de rangos del perfil de volumen (default 24)
    --vp-ventana N    velas hacia atras que cubre el perfil (default 120, 0 = todas)
    --koncorde-cola N cuantos puntos finales de Koncorde exportar (default 120)
    --velas-grafico N velas que se dibujan (default 250, 0 = todas)

Ventana de calculo != ventana de grafico. Todo se calcula sobre la serie completa
que le pases; lo que se recorta es solo lo que se dibuja. La aritmetica que manda
es la de la SMA200: necesita 200 velas para dar su PRIMER valor, asi que para que
la linea cubra un grafico de N velas hacen falta N+199 de historia. Con 250 al
grafico eso son ~450 velas diarias, unos 22 meses. Descargar de menos no rompe
nada, pero deja la SMA200 en null o cubriendo un pedazo del grafico, y el script
avisa exactamente cuantas velas faltan.

Por que existe este script: calcular Koncorde a mano es inviable (encadena PVI, NVI,
MFI, RSI, oscilador de Bollinger y estocastico), y estimar "a ojo" donde esta el POC
de un perfil de volumen produce numeros inventados. Todo lo que sale de aca son
valores reproducibles derivados de la serie real.

Referencia de Koncorde: formula original de Blai5, contrastada contra dos ports a
Pine Script (v4 "KONCORDE ASL" y v5). Mapeo de colores segun el CODIGO de ambos
ports, que coinciden entre si:

    azul   = NVI normalizado          -> manos fuertes (mueven en sesiones flojas)
    verde  = marron + oscp(PVI)       -> manos debiles (siguen el volumen alto)
    marron = (RSI + MFI + BollOsc + Stoch/3) / 2   -> tendencia
    media  = EMA(marron, 15)          -> linea roja de referencia

Ojo: el port v5 tiene el comentario de cabecera invertido (dice verde=NVI,
azul=PVI) pero su propio codigo asigna RS_AZUL desde ta.nvi. Vale el codigo.

marron NO esta centrado en cero: por construccion vive en una banda positiva
(tipicamente 20-100). Sus referencias son su propia media, su maximo historico
("picos nevados") y su minimo historico ("mar"). El cero solo es umbral para azul.

PVI/NVI se calculan en su version clasica multiplicativa (equivalente a ta.pvi /
ta.nvi de TradingView). El port v4 usa una variante que multiplica por el volumen
en lugar de por el indice previo; da otra escala pero la misma lectura cualitativa.

Set de medias moviles: WMA10, WMA21, EMA50, SMA200. Son dos pares con roles
distintos y no hay que mezclarlos. WMA10/WMA21 es el par rapido, el gatillo de
swing sobre grafico diario: su cruce es la senal temprana de cambio de tendencia,
pero solo vale si confluye con Koncorde, MACD y RSI. EMA50/SMA200 es el par
estructural, el que define el regimen (cruce dorado / cruce de la muerte) y el
que suele oficiar de soporte o resistencia dinamica.
"""

import json
import sys
import math
import argparse

# ---------------------------------------------------------------- primitivas


def sma(a, k):
    out = []
    s = 0.0
    for i, v in enumerate(a):
        s += v
        if i >= k:
            s -= a[i - k]
        out.append(s / k if i >= k - 1 else None)
    return out


def wma(a, k):
    """Media ponderada lineal: el dato mas reciente pesa k, el mas viejo pesa 1.

    Equivale a ta.wma de Pine. Reacciona antes que la SMA del mismo largo y
    tambien antes que la EMA, porque descarta de golpe lo que sale de la
    ventana en vez de arrastrarlo con peso decreciente infinito.
    """
    out = [None] * len(a)
    den = k * (k + 1) / 2.0
    for i in range(k - 1, len(a)):
        s = 0.0
        for j in range(k):
            s += a[i - k + 1 + j] * (j + 1)
        out[i] = s / den
    return out


def ema(a, k):
    """EMA sembrada con la SMA de los primeros k valores, como hace Pine."""
    out = [None] * len(a)
    if len(a) < k:
        return out
    alpha = 2.0 / (k + 1)
    prev = sum(a[:k]) / k
    out[k - 1] = prev
    for i in range(k, len(a)):
        prev = (a[i] - prev) * alpha + prev
        out[i] = prev
    return out


def rma(a, k):
    """Media de Wilder, la que usan RSI, ATR y ADX."""
    out = [None] * len(a)
    if len(a) < k:
        return out
    prev = sum(a[:k]) / k
    out[k - 1] = prev
    for i in range(k, len(a)):
        prev = (prev * (k - 1) + a[i]) / k
        out[i] = prev
    return out


def stdev_pop(a, k):
    out = [None] * len(a)
    for i in range(k - 1, len(a)):
        w = a[i - k + 1:i + 1]
        m = sum(w) / k
        out[i] = math.sqrt(sum((x - m) ** 2 for x in w) / k)
    return out


def rolling(a, k, fn):
    out = [None] * len(a)
    for i in range(len(a)):
        w = [x for x in a[max(0, i - k + 1):i + 1] if x is not None]
        out[i] = fn(w) if w else None
    return out


def last_valid(a):
    for v in reversed(a):
        if v is not None:
            return v
    return None


def r(v, d=2):
    return None if v is None else round(v, d)


# ---------------------------------------------------------------- indicadores


def rsi(src, k=14):
    gains, losses = [0.0], [0.0]
    for i in range(1, len(src)):
        ch = src[i] - src[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
    ag, al = rma(gains, k), rma(losses, k)
    out = []
    for g, l in zip(ag, al):
        if g is None or l is None:
            out.append(None)
        elif l == 0:
            out.append(100.0)
        else:
            out.append(100 - 100 / (1 + g / l))
    return out


def macd(closes, fast=12, slow=26, sig=9):
    ef, es = ema(closes, fast), ema(closes, slow)
    line = [(a - b) if (a is not None and b is not None) else None
            for a, b in zip(ef, es)]
    valid = [v for v in line if v is not None]
    sg = ema(valid, sig)
    off = len(line) - len(valid)
    signal = [None] * off + sg
    hist = [(a - b) if (a is not None and b is not None) else None
            for a, b in zip(line, signal)]
    return line, signal, hist


def true_range(o, h, l, c):
    tr = [h[0] - l[0]]
    for i in range(1, len(c)):
        tr.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    return tr


def adx(h, l, c, k=14):
    tr = true_range(None, h, l, c)
    pdm, ndm = [0.0], [0.0]
    for i in range(1, len(c)):
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm.append(up if (up > dn and up > 0) else 0.0)
        ndm.append(dn if (dn > up and dn > 0) else 0.0)
    atr_, sp, sn = rma(tr, k), rma(pdm, k), rma(ndm, k)
    pdi, ndi, dx = [], [], []
    for a, p, n in zip(atr_, sp, sn):
        if not a:
            pdi.append(None); ndi.append(None); dx.append(None); continue
        pi, ni = 100 * p / a, 100 * n / a
        pdi.append(pi); ndi.append(ni)
        dx.append(100 * abs(pi - ni) / (pi + ni) if (pi + ni) else 0.0)
    valid = [v for v in dx if v is not None]
    ad = rma(valid, k)
    return [None] * (len(dx) - len(ad)) + ad, pdi, ndi, atr_


def mfi(h, l, c, vol, k=14):
    tp = [(h[i] + l[i] + c[i]) / 3 for i in range(len(c))]
    out = [None] * len(c)
    for i in range(k, len(c)):
        up = dn = 0.0
        for j in range(i - k + 1, i + 1):
            ch = tp[j] - tp[j - 1]
            if ch > 0:
                up += tp[j] * vol[j]
            elif ch < 0:
                dn += tp[j] * vol[j]
        out[i] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    return out


def stoch(src, h, l, k=14, smooth=3):
    raw = [None] * len(src)
    for i in range(k - 1, len(src)):
        hh, ll = max(h[i - k + 1:i + 1]), min(l[i - k + 1:i + 1])
        raw[i] = 100 * (src[i] - ll) / (hh - ll) if hh > ll else 50.0
    valid = [v for v in raw if v is not None]
    sm = sma(valid, smooth)
    return [None] * (len(raw) - len(sm)) + sm


def volume_index(closes, vol, positive):
    """PVI (positive=True) o NVI (positive=False), version multiplicativa clasica.

    El valor inicial es arbitrario porque Koncorde normaliza el indice contra su
    propia media y su rango, y una constante multiplicativa se cancela.
    """
    idx = [100.0]
    for i in range(1, len(closes)):
        cond = vol[i] > vol[i - 1] if positive else vol[i] < vol[i - 1]
        if cond and closes[i - 1]:
            idx.append(idx[-1] * (1 + (closes[i] - closes[i - 1]) / closes[i - 1]))
        else:
            idx.append(idx[-1])
    return idx


def koncorde(o, h, l, c, vol, m=15, ventana=90):
    """Blai5 Koncorde. Devuelve (verde, marron, azul, media), con None en warm-up."""
    n = len(c)
    tprice = [(o[i] + h[i] + l[i] + c[i]) / 4 for i in range(n)]

    def normalizar(idx, media_idx):
        """(indice - su media) escalado por el rango de esa media en `ventana`.

        Al ser un cociente de diferencias, la constante inicial del indice se
        cancela: da igual arrancar PVI/NVI en 1, 100 o 1000.
        """
        mx, mn = rolling(media_idx, ventana, max), rolling(media_idx, ventana, min)
        out = [None] * n
        for i in range(n):
            if media_idx[i] is None or mx[i] is None or mn[i] is None or mx[i] == mn[i]:
                continue
            out[i] = (idx[i] - media_idx[i]) * 100 / (mx[i] - mn[i])
        return out

    pvi, nvi = volume_index(c, vol, True), volume_index(c, vol, False)
    oscp = normalizar(pvi, ema(pvi, m))   # manos debiles
    azul = normalizar(nvi, ema(nvi, m))   # manos fuertes

    xrsi = rsi(tprice, 14)
    xmf = mfi(h, l, c, vol, 14)
    basis, dev = sma(tprice, 25), stdev_pop(tprice, 25)
    bolosc = [None] * n
    for i in range(n):
        if basis[i] is None or not dev[i]:
            continue
        # banda superior = basis + 2*dev, inferior = basis - 2*dev
        # OB1 = (sup + inf)/2 = basis ; OB2 = sup - inf = 4*dev
        bolosc[i] = ((tprice[i] - basis[i]) / (4 * dev[i])) * 100
    stc = stoch(tprice, h, l, 21, 3)

    marron = [None] * n
    for i in range(n):
        vals = (xrsi[i], xmf[i], bolosc[i], stc[i])
        if any(v is None for v in vals):
            continue
        marron[i] = (xrsi[i] + xmf[i] + bolosc[i] + stc[i] / 3) / 2

    mv = [v for v in marron if v is not None]
    me = ema(mv, m)
    media = [None] * (n - len(me)) + me

    verde = [(marron[i] + oscp[i]) if (marron[i] is not None and oscp[i] is not None)
             else None for i in range(n)]
    return verde, marron, azul, media


# ---------------------------------------------------------- volume profile


def volume_profile(h, l, c, o, vol, fechas, bins=24, ventana=120):
    n = len(c)
    ini = 0 if not ventana or ventana >= n else n - ventana
    H, L = h[ini:], l[ini:]
    lo, hi = min(L), max(H)
    if hi <= lo:
        return None
    step = (hi - lo) / bins
    acc = [{"volumen": 0.0, "alcista": 0.0, "bajista": 0.0} for _ in range(bins)]

    for i in range(ini, n):
        rango = h[i] - l[i]
        up = c[i] >= o[i]
        b0 = min(bins - 1, max(0, int((l[i] - lo) / step)))
        b1 = min(bins - 1, max(0, int((h[i] - lo) / step)))
        if rango <= 0 or b0 == b1:
            tramos = [(b0, 1.0)]
        else:
            tramos = []
            for b in range(b0, b1 + 1):
                bl, bh = lo + b * step, lo + (b + 1) * step
                solap = min(h[i], bh) - max(l[i], bl)
                if solap > 0:
                    tramos.append((b, solap / rango))
            tot = sum(w for _, w in tramos) or 1.0
            tramos = [(b, w / tot) for b, w in tramos]
        for b, w in tramos:
            acc[b]["volumen"] += vol[i] * w
            acc[b]["alcista" if up else "bajista"] += vol[i] * w

    total = sum(a["volumen"] for a in acc)
    if total <= 0:
        return None

    poc_i = max(range(bins), key=lambda b: acc[b]["volumen"])
    lo_i = hi_i = poc_i
    cum = acc[poc_i]["volumen"]
    while cum < total * 0.70 and (lo_i > 0 or hi_i < bins - 1):
        vdn = acc[lo_i - 1]["volumen"] if lo_i > 0 else -1
        vup = acc[hi_i + 1]["volumen"] if hi_i < bins - 1 else -1
        if vup >= vdn:
            hi_i += 1; cum += acc[hi_i]["volumen"]
        else:
            lo_i -= 1; cum += acc[lo_i]["volumen"]

    val, vah = lo + lo_i * step, lo + (hi_i + 1) * step
    poc = lo + (poc_i + 0.5) * step
    prom = total / bins
    px = c[-1]
    if px > vah:
        pos = "sobre la value area"
    elif px < val:
        pos = "bajo la value area"
    elif abs(px - poc) <= step:
        pos = "en el POC"
    elif px > poc:
        pos = "en la mitad alta de la value area"
    else:
        pos = "en la mitad baja de la value area"

    bins_out = []
    for b, a in enumerate(acc):
        bins_out.append({
            "desde": r(lo + b * step), "hasta": r(lo + (b + 1) * step),
            "volumen": round(a["volumen"]),
            "vol_alcista": round(a["alcista"]), "vol_bajista": round(a["bajista"]),
            "es_poc": b == poc_i, "en_value_area": lo_i <= b <= hi_i,
        })
    hvn = [b for b in sorted(bins_out, key=lambda x: -x["volumen"])[:3]]
    lvn = [b for b in bins_out
           if b["volumen"] < prom * 0.45 and not b["en_value_area"]]

    return {
        "timeframe": "Diario", "ventana": n - ini, "bins": bins_out,
        "poc": r(poc), "vah": r(vah), "val": r(val),
        "volumen_total": round(total),
        "pct_en_value_area": r(cum / total * 100, 1),
        "posicion_precio": pos,
        "hvn": [{"desde": b["desde"], "hasta": b["hasta"],
                 "pct_del_total": r(b["volumen"] / total * 100, 1)} for b in hvn],
        "lvn": [{"desde": b["desde"], "hasta": b["hasta"],
                 "pct_del_total": r(b["volumen"] / total * 100, 1)} for b in lvn[:3]],
        "sesgo_flujo": r(sum(b["vol_alcista"] for b in bins_out) / total * 100, 1),
    }


def ultimo_cruce(rapida, lenta, fechas):
    """Ultimo cruce entre dos series de medias: tipo, fecha y velas transcurridas.

    Devuelve None si nunca cruzaron dentro de la historia disponible, que es un
    dato en si mismo: una tendencia sin cruces es una tendencia que no se
    interrumpio.
    """
    n = len(rapida)
    ult = None
    for i in range(1, n):
        a0, b0, a1, b1 = rapida[i - 1], lenta[i - 1], rapida[i], lenta[i]
        if None in (a0, b0, a1, b1):
            continue
        if (a0 <= b0 and a1 > b1) or (a0 >= b0 and a1 < b1):
            ult = {"tipo": "alcista" if a1 > b1 else "bajista",
                   "fecha": fechas[i], "velas_desde": n - 1 - i,
                   "separacion_pct": r((a1 / b1 - 1) * 100, 2) if b1 else None}
    if ult is not None and rapida[-1] is not None and lenta[-1]:
        ult["separacion_pct"] = r((rapida[-1] / lenta[-1] - 1) * 100, 2)
    return ult


def recortar_serie(ps, fechas, series, velas):
    """Arma el bloque `precio_serie` listo para pegar, recortado a las ultimas N.

    La ventana de calculo y la del grafico son cosas distintas y hay que
    separarlas. Una SMA200 necesita 200 velas para dar su PRIMER valor, asi que
    para dibujarla a lo largo de un grafico de N velas hacen falta N+199 de
    historia. Se descarga mucho, se calcula sobre todo, y se muestra la cola.
    """
    n = len(fechas)
    ini = 0 if not velas or velas >= n else n - velas
    out = {"timeframe": "Diario", "fechas": fechas[ini:]}
    if ps.get("ohlc"):
        out["ohlc"] = ps["ohlc"][ini:]
    else:
        out["cierres"] = ps["cierres"][ini:]
    if ps.get("volumen"):
        out["volumen"] = ps["volumen"][ini:]
    out["medias"] = {nm: [r(v) for v in ser[ini:]] for nm, ser in series}
    return out


def estado_medias(c, fechas, series, velas=0):
    """Lectura deterministica del abanico de medias.

    `series` es una lista [(nombre, valores), ...] ordenada de mas rapida a mas
    lenta. Sale de aca todo lo que el modelo podria estimar mal a ojo: el orden
    del abanico, la distancia porcentual del precio a cada media, la pendiente
    de cada una en las ultimas 10 velas y los dos cruces que importan.
    """
    px = c[-1]
    act = [(nm, last_valid(v)) for nm, v in series]
    vivas = [(nm, v) for nm, v in act if v is not None]

    orden = " > ".join(
        [x[0] for x in sorted(vivas + [("Precio", px)], key=lambda t: -t[1])]
    ).replace("Precio", "P")

    pend = {}
    for nm, v in series:
        vv = [x for x in v if x is not None]
        if len(vv) >= 11 and vv[-11]:
            pend[nm] = r((vv[-1] / vv[-11] - 1) * 100, 2)
        else:
            pend[nm] = None

    d = dict(series)
    nombres = [nm for nm, _ in series]
    sin_dato = [nm for nm, v in act if v is None]

    # La alineacion se evalua sobre las medias que tienen dato. Si falta la
    # SMA200 no se puede hablar de abanico completo: queda dicho en `sin_dato`.
    vals = [v for _, v in vivas]
    alineacion = "mixta"
    if len(vals) >= 2:
        if px > vals[0] and all(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
            alineacion = "alcista_completa" if not sin_dato else "alcista_parcial"
        elif px < vals[0] and all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
            alineacion = "bajista_completa" if not sin_dato else "bajista_parcial"

    visible = len(fechas) if not velas else min(velas, len(fechas))
    cr = ultimo_cruce(d[nombres[0]], d[nombres[1]], fechas)
    ce = ultimo_cruce(d[nombres[2]], d[nombres[3]], fechas)
    for x in (cr, ce):
        if x:
            x["visible_en_grafico"] = x["velas_desde"] < visible

    return {
        "orden": orden,
        "alineacion": alineacion,
        "sin_dato": sin_dato,
        "velas_calculadas": len(fechas),
        "actuales": {nm: r(v) for nm, v in act},
        "distancia_pct": {nm: r((px / v - 1) * 100, 2) if v else None
                          for nm, v in act},
        "pendiente_10d_pct": pend,
        "cruce_rapido": cr,
        "cruce_estructural": ce,
    }


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada"); ap.add_argument("salida")
    ap.add_argument("--vp-bins", type=int, default=24)
    ap.add_argument("--vp-ventana", type=int, default=120)
    ap.add_argument("--koncorde-cola", type=int, default=120)
    ap.add_argument("--velas-grafico", type=int, default=250,
                    help="velas que se dibujan en el grafico (0 = todas). El "
                         "calculo usa siempre la serie completa")
    a = ap.parse_args()

    raw = json.load(open(a.entrada, encoding="utf-8"))
    ps = raw.get("precio_serie", raw)
    fechas = ps["fechas"]
    if ps.get("ohlc"):
        o = [x[0] for x in ps["ohlc"]]; h = [x[1] for x in ps["ohlc"]]
        l = [x[2] for x in ps["ohlc"]]; c = [x[3] for x in ps["ohlc"]]
    else:
        c = ps["cierres"]; o = h = l = c
        print("AVISO: sin OHLC, el perfil de volumen y Koncorde pierden precision.",
              file=sys.stderr)
    vol = ps.get("volumen")
    if not vol:
        print("ERROR: se necesita volumen para el perfil de volumen y Koncorde.",
              file=sys.stderr)
        sys.exit(2)
    n = len(c)
    if n < 130:
        print(f"AVISO: {n} velas. Koncorde necesita ~130 para estabilizarse "
              f"(usa ventanas de 90) y el perfil gana definicion con mas historia.",
              file=sys.stderr)
    vis = min(a.velas_grafico, n) if a.velas_grafico else n
    if n < 200:
        print(f"AVISO: {n} velas. La SMA200 necesita 200 para dar su primer valor. "
              f"Descarga {200 - n} velas mas para tenerla, y {vis + 199 - n} mas "
              f"para que se dibuje a lo largo de todo el grafico.", file=sys.stderr)
    elif n < vis + 199:
        print(f"AVISO: {n} velas de calculo para {vis} de grafico. La SMA200 se "
              f"calcula pero solo cubre las ultimas {n - 199} velas del grafico; "
              f"con {vis + 199} velas cubriria todo.", file=sys.stderr)

    rsi14 = rsi(c, 14)
    ml, msig, mh = macd(c)
    ad, pdi, ndi, atr_ = adx(h, l, c, 14)
    volsma = sma(vol, 20)
    w10, w21 = wma(c, 10), wma(c, 21)
    e50, s200 = ema(c, 50), sma(c, 200)
    med_series = [("WMA10", w10), ("WMA21", w21), ("EMA50", e50), ("SMA200", s200)]
    stc = stoch(c, h, l, 14, 3)
    bb_basis, bb_dev = sma(c, 20), stdev_pop(c, 20)
    bb_pct = None
    if bb_basis[-1] and bb_dev[-1]:
        up, dn = bb_basis[-1] + 2 * bb_dev[-1], bb_basis[-1] - 2 * bb_dev[-1]
        bb_pct = (c[-1] - dn) / (up - dn) * 100 if up > dn else None

    verde, marron, azul, media = koncorde(o, h, l, c, vol)
    idx = [i for i in range(n) if verde[i] is not None and azul[i] is not None]
    cola = idx[-a.koncorde_cola:] if idx else []
    kb = None
    if cola:
        u = cola[-1]
        az, ve, ma = azul[u], verde[u], marron[u]
        prev = cola[max(0, len(cola) - 11)]
        d_az = az - (azul[prev] if azul[prev] is not None else az)
        d_ve = ve - (verde[prev] if verde[prev] is not None else ve)

        # Lectura de Blai5: lo que importa es quien esta comprando, no el nivel
        # absoluto. Mano fuerte entrando con mano debil quieta es el suelo tipico;
        # mano debil eufOrica con mano fuerte saliendo es el techo tipico.
        if az > 0 and d_az > 0 and d_ve <= 0:
            estado, det = "Acumulacion", ("Mano fuerte comprando mientras la debil "
                                          "no acompana: patron de suelo.")
        elif az > 0 and d_az > 0:
            estado, det = "Acumulacion", "Mano fuerte sumando posicion."
        elif az < 0 and d_az < 0 and d_ve > 0:
            estado, det = "Distribucion", ("Mano fuerte saliendo mientras la debil "
                                           "compra: patron de techo.")
        elif az < 0 and d_az < 0:
            estado, det = "Distribucion", "Mano fuerte reduciendo posicion."
        elif az > 0:
            estado, det = "Posicionado", "Mano fuerte dentro pero sin agregar."
        else:
            estado, det = "Neutral", "Sin sesgo claro de mano fuerte."

        mv = [marron[i] for i in idx if marron[i] is not None]
        kb = {
            "timeframe": "Diario",
            "fechas": [fechas[i] for i in cola],
            "verde": [r(verde[i], 1) for i in cola],
            "marron": [r(marron[i], 1) for i in cola],
            "azul": [r(azul[i], 1) for i in cola],
            "media": [r(media[i], 1) if media[i] is not None else None for i in cola],
            "azul_actual": r(az, 1), "verde_actual": r(ve, 1),
            "marron_actual": r(ma, 1),
            "media_actual": r(media[u], 1) if media[u] is not None else None,
            "azul_delta_10d": r(d_az, 1), "verde_delta_10d": r(d_ve, 1),
            "picos_nevados": r(max(mv), 1) if mv else None,   # maximo historico marron
            "mar": r(min(mv), 1) if mv else None,             # minimo historico marron
            "estado": estado, "detalle_auto": det,
        }

    out = {
        "ultimo": {
            "fecha": fechas[-1], "close": r(c[-1]),
            "rsi14": r(rsi14[-1], 1),
            "macd": r(ml[-1], 3), "macd_signal": r(msig[-1], 3), "macd_hist": r(mh[-1], 3),
            "adx14": r(ad[-1], 1), "plus_di": r(pdi[-1], 1), "minus_di": r(ndi[-1], 1),
            "atr14": r(atr_[-1]),
            "atr_pct": r(atr_[-1] / c[-1] * 100, 2) if atr_[-1] else None,
            "vol_rel20": r(vol[-1] / volsma[-1], 2) if volsma[-1] else None,
            "wma10": r(w10[-1]), "wma21": r(w21[-1]),
            "ema50": r(e50[-1]), "sma200": r(s200[-1]),
            "estocastico": r(stc[-1], 1), "bb_pct_b": r(bb_pct, 1),
        },
        "precio_serie": recortar_serie(ps, fechas, med_series, a.velas_grafico),
        "medias_estado": estado_medias(c, fechas, med_series, a.velas_grafico),
        "volume_profile": volume_profile(h, l, c, o, vol, fechas,
                                         a.vp_bins, a.vp_ventana),
        "koncorde": kb,
    }
    json.dump(out, open(a.salida, "w", encoding="utf-8"), ensure_ascii=False)

    u = out["ultimo"]
    print(f"OK: {a.salida}")
    print(f"  Cierre {u['close']} al {u['fecha']}: {n} velas calculadas, "
          f"{len(out['precio_serie']['fechas'])} al grafico")
    print(f"  RSI {u['rsi14']} | ADX {u['adx14']} (+DI {u['plus_di']} / -DI {u['minus_di']})"
          f" | ATR {u['atr14']} ({u['atr_pct']}%) | Vol rel {u['vol_rel20']}x")
    me = out["medias_estado"]
    print(f"  Medias: {me['orden']} ({me['alineacion']})")
    if me["sin_dato"]:
        print(f"    AVISO: sin dato para {', '.join(me['sin_dato'])}. "
              f"La SMA200 necesita 200 velas y hay {n}. No la cites en el informe.",
              file=sys.stderr)
    cr = me["cruce_rapido"]
    if cr:
        print(f"    Cruce WMA10/WMA21 {cr['tipo']} el {cr['fecha']} "
              f"({cr['velas_desde']} velas atras, separacion {cr['separacion_pct']}%)")
    ce = me["cruce_estructural"]
    if ce:
        print(f"    Cruce EMA50/SMA200 {ce['tipo']} el {ce['fecha']} "
              f"({ce['velas_desde']} velas atras)")
    vp = out["volume_profile"]
    if vp:
        print(f"  Perfil de volumen sobre {vp['ventana']} velas: "
              f"POC {vp['poc']} | VA {vp['val']}-{vp['vah']} | precio {vp['posicion_precio']}")
    if kb:
        print(f"  Koncorde: azul {kb['azul_actual']} (10d {kb['azul_delta_10d']:+}) | "
              f"verde {kb['verde_actual']} | estado {kb['estado']}")


if __name__ == "__main__":
    main()
