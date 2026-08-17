#!/usr/bin/env python3
"""
Prepara la skill para instalar y verifica que funcione.

    python3 build.py                 # sincroniza instalar-skills/analisis-tecnico-boa
    python3 build.py <destino>       # ademas la copia a otro directorio

Despues hay que correr el instalador, que es lo que la deja en el directorio de
skills de la app. Vive en el proyecto vecino "Instalador de Skills" y se le
apunta -Origen a la carpeta instalar-skills/ de aca.

POR QUE NO SE GENERA UN .skill
------------------------------
El importador de archivos .skill de la app no instala un paquete: instala un
documento. Toma SKILL.md, le parsea el frontmatter para sacar name y
description, guarda el cuerpo como instrucciones y descarta TODO el resto del
zip. No hay ningun paso que copie scripts/, assets/ ni references/. El sintoma
es traicionero: la skill se instala sin error, se dispara bien, y el modelo lee
instrucciones que mandan a ejecutar scripts que no existen. Como no puede,
improvisa los indicadores.

Esto se comprobo, no se supone:
  - Las 19 skills instaladas por esa via tenian exactamente 1 archivo.
  - No es profundidad de subcarpetas: un paquete completamente plano se perdio
    igual. (Fue una hipotesis previa, y era falsa.)
  - No es filtro por extension ni materializacion perezosa.
  - El manifiesto de skills solo guarda metadata y ni un campo que apunte a un
    archivo o a un paquete, que es lo que existiria si preservara bundles.

EL CANAL QUE SI FUNCIONA
------------------------
El runtime no tiene ese problema: lee la carpeta de cada skill tal cual esta en
disco, sin ningun manifiesto. Las skills que vienen incluidas con la app
conservan varios archivos (frontend-design tiene su LICENSE.txt, pdf-reading
tiene ademas REFERENCE.md), asi que el formato soporta multiples archivos de
sobra. El unico que los tira es el importador.

Entonces alcanza con copiar la carpeta al directorio de skills de la app, que es
persistente y a nivel de cuenta, bajo:

    %LOCALAPPDATA%\\Claude-3p\\local-agent-mode-sessions\\skills-plugin\\...\\skills

De eso se ocupa el instalador del proyecto "Instalador de Skills". Verificado
end-to-end el 2026-08-17: los scripts corren desde la skill ya instalada y
generan el informe completo.

Descartado por evidencia: los "skills directories" de Claude Code
(<proyecto>\\.claude\\skills\\ y ~\\.claude\\skills\\) y los plugins @skills-dir.
Esta app no los escanea. Se probo con el plugin armado y no cargo.
"""

import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(RAIZ, "analisis-tecnico-boa")
STAGING = os.path.join(RAIZ, "instalar-skills", "analisis-tecnico-boa")
EJEMPLOS = os.path.join(RAIZ, "examples")


def archivos(base):
    out = []
    for dp, dirs, fn in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".claude-plugin")]
        for f in sorted(fn):
            if not f.endswith((".pyc", ".DS_Store")):
                out.append(os.path.join(dp, f))
    return sorted(out)


def normalizar(paths):
    """UTF-8 sin BOM y saltos LF.

    No es cosmetica: el frontmatter se rompe con BOM o con CRLF raros despues
    de un round-trip por Windows u OneDrive.
    """
    tocados = 0
    for p in paths:
        b = open(p, "rb").read()
        nb = b[3:] if b.startswith(b"\xef\xbb\xbf") else b
        nb = nb.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if nb != b:
            open(p, "wb").write(nb)
            tocados += 1
    return tocados


def verificar_frontmatter(ruta):
    b = open(ruta, "rb").read()
    problemas = []
    if b.startswith(b"\xef\xbb\xbf"):
        problemas.append("SKILL.md arranca con BOM")
    if not b.startswith(b"---\n"):
        problemas.append("el frontmatter no arranca en la primera linea")
    bloque = b.split(b"\n---\n", 1)[0][4:]
    try:
        bloque.decode("ascii")
    except UnicodeDecodeError:
        problemas.append("el frontmatter tiene caracteres no ASCII "
                         "(sobreviven mal a un round-trip por Windows)")
    for k in (b"name:", b"description:"):
        if not any(l.startswith(k) for l in bloque.split(b"\n")):
            problemas.append(f"falta {k.decode()} en el frontmatter")
    return problemas


def sincronizar(destino):
    """Copia el arbol de la skill al destino. Devuelve los huerfanos que quedaron.

    Sobreescribe en el lugar en vez de borrar y recrear: algunos destinos estan
    sobre mounts que no permiten unlink (OneDrive, FUSE del sandbox). Los
    archivos que sobran se intentan borrar, y si no se puede se reportan en vez
    de abortar.
    """
    os.makedirs(destino, exist_ok=True)
    shutil.copytree(FUENTE, destino, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                  ".DS_Store"))
    esperados = {os.path.relpath(p, FUENTE).replace("\\", "/")
                 for p in archivos(FUENTE)}
    quedan = []
    for dp, dirs, fn in os.walk(destino):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, destino).replace("\\", "/")
            if rel in esperados or f.endswith(".pyc"):
                continue
            try:
                os.unlink(p)
            except OSError:
                quedan.append(rel)
    return quedan


def verificar(destino):
    """Corre los scripts DESDE el destino y genera un informe real.

    Esta verificacion vale porque ejecuta el mismo arbol que se va a copiar al
    directorio de la app. La version vieja de este script validaba un zip
    desempaquetado en un temporal, que no era lo que se instalaba: daba verde
    con la skill rota.
    """
    problemas = []
    if not os.path.isfile(os.path.join(destino, "SKILL.md")):
        problemas.append("falta SKILL.md en la raiz de la skill")

    import tempfile
    with tempfile.TemporaryDirectory(prefix="verif_") as tmp:
        calc = os.path.join(tmp, "calc.json")
        html = os.path.join(tmp, "informe.html")
        r = subprocess.run([sys.executable,
                            os.path.join(destino, "scripts", "compute_indicators.py"),
                            os.path.join(EJEMPLOS, "serie_nvda.json"), calc,
                            "--vp-ventana", "90"], capture_output=True, text=True)
        if r.returncode != 0:
            problemas.append("compute_indicators.py falla: " + r.stderr.strip()[:200])
        r = subprocess.run([sys.executable,
                            os.path.join(destino, "scripts", "build_report.py"),
                            os.path.join(EJEMPLOS, "demo_final.json"), html],
                           capture_output=True, text=True)
        if r.returncode != 0:
            problemas.append("build_report.py falla: " + r.stderr.strip()[:200])
        elif not os.path.exists(html):
            problemas.append("build_report.py no genero el HTML")
        else:
            cuerpo = open(html, encoding="utf-8").read()
            kb = len(cuerpo) / 1024
            if kb < 60:
                problemas.append(f"el informe pesa {kb:.0f} KB: el template no "
                                 f"se inyecto entero")
            if "/*__DATA__*/null" in cuerpo:
                problemas.append("el marcador de datos quedo sin reemplazar")
    return problemas


def main():
    if not os.path.isdir(FUENTE):
        print(f"ERROR: no existe {FUENTE}", file=sys.stderr)
        sys.exit(2)

    paths = archivos(FUENTE)
    n = normalizar(paths)
    print(f"Normalizados a UTF-8 sin BOM + LF: {n} modificado(s), "
          f"{len(paths)} revisado(s)")

    problemas = verificar_frontmatter(os.path.join(FUENTE, "SKILL.md"))
    if problemas:
        print("\nERROR en SKILL.md:", file=sys.stderr)
        for x in problemas:
            print(f"  - {x}", file=sys.stderr)
        sys.exit(1)
    print("Frontmatter OK: name y description presentes, ASCII puro, sin BOM")

    quedan = sincronizar(STAGING)
    print("\nSincronizada en instalar-skills/analisis-tecnico-boa/")
    if quedan:
        print("  AVISO: sobran archivos que no se pudieron borrar "
              "(el mount no permite unlink). Borralos a mano:")
        for r in quedan:
            print(f"    {r}")

    print("\nVerificando: se ejecutan los scripts desde ahi...")
    fallas = verificar(STAGING)
    if fallas:
        print("\nERROR: no pasa la verificacion:", file=sys.stderr)
        for x in fallas:
            print(f"  - {x}", file=sys.stderr)
        sys.exit(1)
    print("  OK: compute_indicators.py y build_report.py corren desde el staging")
    print("  OK: el informe se genera completo y con los datos inyectados")

    if len(sys.argv) > 1:
        extra = os.path.join(os.path.abspath(sys.argv[1]), "analisis-tecnico-boa")
        sincronizar(extra)
        print(f"  copiada tambien a {extra}")

    print("\nAhora, para que la app la vea: cerra la app, corre el instalador")
    print("desde el proyecto \"Instalador de Skills\" apuntando a este staging:")
    print("  cd \"...\\Projects\\Instalador de Skills\"")
    print("  powershell -ExecutionPolicy Bypass -File .\\instalar-skills.ps1 "
          "-Origen \"%s\"" % os.path.join(RAIZ, "instalar-skills"))
    print("y volve a abrirla.")


if __name__ == "__main__":
    main()
