#!/usr/bin/env python3
"""
Verifica que el proyecto este completo y sano en su ubicacion definitiva.

    python3 verificar.py

Hace tres controles y despues encadena el build y la suite de tests:

1. INVENTARIO -- que esten los 16 archivos fuente, que ninguno este vacio y que
   su contenido coincida con el hash de referencia. Detecta archivos faltantes,
   sobrantes o modificados. El hash se calcula sobre el contenido normalizado
   (sin BOM, con saltos LF), asi que un cambio de fin de linea no dispara un
   falso positivo aca: eso se reporta aparte en el control 2.

2. CODIFICACION -- BOM, saltos CRLF y caracteres no ASCII en el frontmatter de
   SKILL.md. Este es el control que importa de verdad despues de mover archivos
   por Windows u OneDrive: es exactamente lo que produce el error
   "SKILL.md frontmatter missing name or description" al instalar la skill.

3. ENTORNO -- version de Python y presencia de Node, que hace falta para el
   bloque de verificacion de JavaScript de la suite.

Despues corre build.py y tests/run_all.py. Si todo da verde, el proyecto quedo
bien copiado y la skill esta lista para instalar desde dist/.
"""

import hashlib
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))

# sha256 (16 primeros caracteres) del contenido normalizado, y tamano original
REFERENCIA = {
    "README.md": ("1f077d5903e14e59", 7270),
    "build.py": ("b4949ff959a34868", 3714),
    "analisis-tecnico-boa/SKILL.md": ("1f728b7635dfe0f7", 17053),
    "analisis-tecnico-boa/assets/report_template.html": ("69711b1f00a92b67", 64254),
    "analisis-tecnico-boa/references/indicadores.md": ("6591eaacea5be37e", 13775),
    "analisis-tecnico-boa/references/schema.md": ("73e68419036a0d85", 15767),
    "analisis-tecnico-boa/references/scoring.md": ("726fb1fd4f1fb996", 7582),
    "analisis-tecnico-boa/scripts/build_report.py": ("9eb1f7ddfdb067fc", 10131),
    "analisis-tecnico-boa/scripts/compute_indicators.py": ("01696b950930cd91", 18526),
    "examples/demo_final.json": ("85cf3471fb2378fd", 28924),
    "examples/informe_NVDA_demo.html": ("f78c18ab45d57a55", 93310),
    "examples/serie_nvda.json": ("078e88ca0f54f506", 8852),
    "tests/check.js": ("7c308e561eec8207", 938),
    "tests/domshim.js": ("d90834a7b6cb63b7", 1536),
    "tests/interact.js": ("84ac3485e8c4b1d9", 1881),
    "tests/run_all.py": ("d5e0ee574a422a57", 7124),
}

PROBLEMAS = []
AVISOS = []


def normalizar(b):
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def encontrados():
    out = set()
    for dp, dirs, fn in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "dist")]
        for f in fn:
            if f.endswith((".pyc", ".DS_Store")) or f == os.path.basename(__file__):
                continue
            out.add(os.path.relpath(os.path.join(dp, f), RAIZ).replace("\\", "/"))
    return out


def inventario():
    print("\n[1] Inventario de archivos")
    hay = encontrados()
    faltan = sorted(set(REFERENCIA) - hay)
    sobran = sorted(hay - set(REFERENCIA))

    for p in faltan:
        PROBLEMAS.append(f"FALTA el archivo {p}")
        print(f"  FALTA    {p}")

    for p, (sha_ref, bytes_ref) in sorted(REFERENCIA.items()):
        if p in faltan:
            continue
        b = open(os.path.join(RAIZ, p), "rb").read()
        if not b:
            PROBLEMAS.append(f"{p} esta vacio")
            print(f"  VACIO    {p}")
            continue
        sha = hashlib.sha256(normalizar(b)).hexdigest()[:16]
        if sha == sha_ref:
            extra = "" if len(b) == bytes_ref else f"  (fin de linea distinto: {len(b)} bytes vs {bytes_ref})"
            print(f"  OK       {p}{extra}")
        else:
            PROBLEMAS.append(f"{p} tiene contenido distinto al de referencia")
            print(f"  DISTINTO {p}  (sha {sha} != {sha_ref})")

    for p in sobran:
        AVISOS.append(f"archivo extra: {p}")
        print(f"  EXTRA    {p}  (no molesta, pero no venia en el paquete)")

    d = os.path.join(RAIZ, "dist")
    if os.path.isdir(d):
        paq = [f for f in os.listdir(d) if f.endswith((".skill", ".zip"))]
        print(f"  OK       dist/ presente con {len(paq)} paquete(s): {', '.join(sorted(paq)) or 'ninguno'}")
    else:
        AVISOS.append("no existe dist/; build.py la crea sola")
        print("  AVISO    no existe dist/  (build.py la crea)")


def codificacion():
    print("\n[2] Codificacion (lo que rompe la instalacion de la skill)")
    texto = [p for p in REFERENCIA if p.endswith((".md", ".py", ".js", ".json", ".html"))]
    con_bom, con_crlf = [], []
    for p in texto:
        ruta = os.path.join(RAIZ, p)
        if not os.path.exists(ruta):
            continue
        b = open(ruta, "rb").read()
        if b.startswith(b"\xef\xbb\xbf"):
            con_bom.append(p)
        if b"\r\n" in b:
            con_crlf.append(p)

    if con_bom:
        AVISOS.append(f"{len(con_bom)} archivo(s) con BOM")
        print(f"  AVISO    {len(con_bom)} archivo(s) con BOM: {', '.join(con_bom[:4])}")
        print("           es lo que rompe la instalacion, pero build.py lo saca")
        print("           al empaquetar, asi que se corrige solo en el paso 4")
    else:
        print("  OK       ningun archivo tiene BOM")

    if con_crlf:
        print(f"  AVISO    {len(con_crlf)} archivo(s) con saltos CRLF (Windows): {', '.join(con_crlf[:4])}")
        print("           no rompe nada; build.py normaliza a LF al empaquetar")
        AVISOS.append(f"{len(con_crlf)} archivo(s) con CRLF")
    else:
        print("  OK       saltos de linea LF en todos los archivos")

    sk = os.path.join(RAIZ, "analisis-tecnico-boa", "SKILL.md")
    if not os.path.exists(sk):
        PROBLEMAS.append("no existe SKILL.md")
        print("  FALTA    SKILL.md")
        return
    b = normalizar(open(sk, "rb").read())
    if not b.startswith(b"---\n"):
        PROBLEMAS.append("el frontmatter de SKILL.md no arranca en la primera linea")
        print("  ERROR    el frontmatter no arranca en la linea 1")
        return
    bloque = b.split(b"\n---\n", 1)[0][4:]
    try:
        bloque.decode("ascii")
        print("  OK       frontmatter en ASCII puro (sobrevive round-trips por Windows)")
    except UnicodeDecodeError:
        PROBLEMAS.append("el frontmatter de SKILL.md tiene caracteres no ASCII")
        print("  ERROR    el frontmatter tiene caracteres no ASCII")
    faltantes = [k for k in ("name:", "description:")
                 if not any(l.startswith(k.encode()) for l in bloque.split(b"\n"))]
    if faltantes:
        PROBLEMAS.append(f"el frontmatter no tiene {', '.join(faltantes)}")
        print(f"  ERROR    el frontmatter no tiene {', '.join(faltantes)}")
    else:
        print("  OK       frontmatter con name y description")


def entorno():
    print("\n[3] Entorno")
    v = sys.version_info
    ok = v >= (3, 7)
    print(f"  {'OK      ' if ok else 'ERROR   '} Python {v.major}.{v.minor}.{v.micro}"
          + ("" if ok else "  (hace falta 3.7 o superior)"))
    if not ok:
        PROBLEMAS.append("Python demasiado viejo")
    node = shutil.which("node")
    if node:
        try:
            ver = subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip()
        except Exception:
            ver = "?"
        print(f"  OK       Node {ver}")
    else:
        AVISOS.append("Node no instalado: la suite saltea la verificacion del JavaScript")
        print("  AVISO    Node no esta instalado")
        print("           la suite corre igual pero saltea la verificacion del JavaScript,")
        print("           que es la que atrapa errores de runtime en el informe")


def paquete():
    """El cargador exige SKILL.md en la RAIZ del zip, no dentro de una carpeta."""
    print("\n[6] Paquete generado")
    p = os.path.join(RAIZ, "dist", "analisis-tecnico-boa.skill")
    if not os.path.exists(p):
        PROBLEMAS.append("build.py no dejo dist/analisis-tecnico-boa.skill")
        print("  ERROR    no existe dist/analisis-tecnico-boa.skill")
        return
    import zipfile
    with zipfile.ZipFile(p) as z:
        nombres = z.namelist()
    if "SKILL.md" in nombres:
        print(f"  OK       SKILL.md en la raiz del zip, {len(nombres)} archivo(s) en total")
    else:
        PROBLEMAS.append("SKILL.md no esta en la raiz del zip")
        print("  ERROR    SKILL.md no esta en la raiz del zip")
    for req in ("assets/report_template.html", "scripts/compute_indicators.py",
                "scripts/build_report.py"):
        if req in nombres:
            print(f"  OK       {req}")
        else:
            PROBLEMAS.append(f"el paquete no incluye {req}")
            print(f"  ERROR    el paquete no incluye {req}")


def encadenar(nombre, cmd):
    print(f"\n{nombre}")
    r = subprocess.run([sys.executable] + cmd, cwd=RAIZ, capture_output=True, text=True)
    salida = (r.stdout + r.stderr).strip()
    for l in salida.splitlines():
        print("  " + l)
    if r.returncode != 0:
        PROBLEMAS.append(f"{nombre} termino con error")
    return r.returncode == 0


def main():
    print("=" * 66)
    print("VERIFICACION DEL PROYECTO")
    print(RAIZ)
    print("=" * 66)

    inventario()
    codificacion()
    entorno()

    if PROBLEMAS:
        print("\n" + "=" * 66)
        print(f"{len(PROBLEMAS)} problema(s) encontrado(s). No sigo con el build ni los tests:")
        for p in PROBLEMAS:
            print(f"  - {p}")
        print("=" * 66)
        return 1

    encadenar("[4] Empaquetado -- build.py", ["build.py"])
    encadenar("[5] Suite de tests -- tests/run_all.py",
              [os.path.join("tests", "run_all.py")])
    paquete()

    print("\n" + "=" * 66)
    if PROBLEMAS:
        print(f"{len(PROBLEMAS)} problema(s):")
        for p in PROBLEMAS:
            print(f"  - {p}")
        print("=" * 66)
        return 1
    print("PROYECTO COMPLETO Y VERIFICADO")
    if AVISOS:
        print(f"\n{len(AVISOS)} aviso(s) sin consecuencias:")
        for a in AVISOS:
            print(f"  - {a}")
    print("\nLa skill esta lista: arrastra dist/analisis-tecnico-boa.skill")
    print("a la lista de skills de Claude para instalarla.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
