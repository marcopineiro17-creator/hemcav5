#!/usr/bin/env python3
"""Construye el bloque del MAPA DE PROPIEDADES para el contenedor de codigo
de Hostinger.

Se escribe aqui en tres piezas (CSS, maquetacion y guion) y este programa
las une y las revisa antes de publicar.

A diferencia de los otros bloques, este SI depende de recursos externos:
Firebase para leer la cartera y Leaflet para el mapa. La revision los
permite de forma explicita -- por lista blanca, no por omision -- y sigue
exigiendo todo lo demas.
"""
import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SALIDA = os.path.join(RAIZ, "mapa-embed-hostinger.html")
CONTENEDOR = "cpm-mapa"
# Prefijos con los que puede empezar un selector. El segundo es para las
# capas que se inyectan en <body> y no pueden heredar del contenedor.
PREFIJOS = ("#cpm-mapa", ".cpm-mp-")
# Origenes externos permitidos, uno por uno y con su motivo.
CDN_OK = {
    "www.gstatic.com": "Firebase (lectura de la cartera)",
    "cdn.jsdelivr.net": "respaldo de Firebase y Leaflet",
    "unpkg.com": "Leaflet (el mapa)",
    "tile.openstreetmap.org": "teselas del mapa de calles",
    "server.arcgisonline.com": "teselas de satelite y de calles de Esri",
    "www.esri.com": "atribucion obligatoria de las imagenes",
    "firebasestorage.googleapis.com": "logotipos de CPM",
    "assets.zyrosite.com": "fotos alojadas en Hostinger",
    "fonts.googleapis.com": "tipografia Montserrat",
    "www.openstreetmap.org": "atribucion obligatoria del mapa",
    "maps.app.goo.gl": "enlaces de ubicacion de las propiedades",
    "wa.me": "WhatsApp",
    "www.cpmempresarial.com": "paginas del propio sitio",
    "propiedades-cpm.firebaseapp.com": "dominio de autenticacion de Firebase",
}


def lee(nombre):
    return open(os.path.join(AQUI, nombre), encoding="utf-8").read().strip()


def sin_comentarios(s):
    """Quita comentarios CSS y HTML. Las revisiones se hacen sobre esto: los
    propios comentarios explican los problemas y nombran las cadenas que se
    persiguen, y sin esto se delatarian a si mismos."""
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)


def quita_keyframes(css):
    """Saca los bloques @keyframes antes de revisar el acotado: dentro, los
    'selectores' son from/to y porcentajes, que nunca llevan el id."""
    fuera, i = [], 0
    while True:
        m = re.search(r"@keyframes[^{]*\{", css[i:])
        if not m:
            fuera.append(css[i:])
            break
        ini = i + m.start()
        fuera.append(css[i:ini])
        j, prof = i + m.end(), 1
        while j < len(css) and prof:
            if css[j] == "{":
                prof += 1
            elif css[j] == "}":
                prof -= 1
            j += 1
        i = j
    return "".join(fuera)


def revisa(s):
    problemas = []
    limpio = sin_comentarios(s)
    bajo = limpio.lower()

    # 1. Sintaxis del guion. Un error aqui no da error visible en la pagina:
    #    el bloque simplemente se queda muerto.
    for i, js in enumerate(re.findall(r"<script>(.*?)</script>", s, re.S)):
        f = os.path.join(tempfile.gettempdir(), "chk_mapa_%d.js" % i)
        open(f, "w", encoding="utf-8").write(js)
        r = subprocess.run(["node", "--check", f], capture_output=True, text=True)
        if r.returncode:
            linea = (r.stderr.split("\n") + ["", "", ""])[2].strip()[:80]
            problemas.append("guion %d invalido: %s" % (i, linea))

    # 2. Etiquetas de documento: esto va DENTRO de otra pagina.
    #    Ojo: '<head' tambien casa con '<header>', asi que la maquetacion no
    #    puede usar esa etiqueta. Es a proposito.
    for t in ["<!doctype", "<html", "<head", "<body"]:
        if t in bajo:
            problemas.append("contiene " + t)

    # 3. Etiquetas desparejadas.
    if s.count("<style>") != s.count("</style>"):
        problemas.append("etiquetas <style> desparejadas")
    if s.count("<script") != s.count("</script>"):
        problemas.append("etiquetas <script> desparejadas")

    # 4. Origenes externos: solo los declarados.
    for host in set(re.findall(r"https?://([a-z0-9.\-]+)", limpio, re.I)):
        base = re.sub(r"^\{s\}\.", "", host.lower())
        if base not in CDN_OK:
            problemas.append("origen externo no declarado: " + host)

    # 5. Alturas de viewport sin acotar: realimentan dentro del iframe.
    for m in re.finditer(r"[:\s(]([0-9.]+)(svh|vh)\b", limpio):
        ctx = limpio[max(0, m.start() - 60):m.start()]
        if "vh-real" in ctx or "clamp(" in ctx:
            continue
        problemas.append("altura de viewport sin acotar: " + m.group(0).strip())

    # 6. Todo el CSS acotado. Un selector suelto le cambia el aspecto al
    #    editor del constructor y al resto del sitio.
    css = quita_keyframes(sin_comentarios("\n".join(re.findall(r"<style>(.*?)</style>", s, re.S))))
    sueltos = []
    for bloque in re.split(r"\}", css):
        if "{" not in bloque:
            continue
        selector = bloque.rsplit("{", 1)[0].strip()
        if not selector or selector.startswith("@") or selector.endswith(")"):
            continue
        for parte in selector.split(","):
            parte = parte.strip()
            if not parte or parte.startswith("@"):
                continue
            if not parte.startswith(PREFIJOS):
                sueltos.append(parte[:60])
    if sueltos:
        problemas.append("%d selectores fuera de los prefijos permitidos: %s"
                         % (len(sueltos), "; ".join(sueltos[:4])))

    # 7. Ningun enlace relativo: dentro del iframe navegan por dentro.
    for m in re.finditer(r'href="(/[^/][^"]*)"', s):
        problemas.append("enlace relativo: " + m.group(1))

    return problemas


def main():
    css = lee("mapa_css.txt")
    html = lee("mapa_html.txt")
    js = lee("mapa_js.txt")
    cabecera = lee("cabecera.js")

    partes = [
        "<!-- =====================================================================",
        "     CPM · MAPA DE PROPIEDADES",
        "     Bloque para el contenedor de codigo de Hostinger.",
        "     Lee la coleccion publica 'catalogo_publico' de Firebase y pinta la",
        "     cartera sobre un mapa navegable, con su lista sincronizada.",
        "     Se pega tal cual: no lleva etiquetas de documento y todo su CSS esta",
        "     acotado a #cpm-mapa (y a .cpm-mp-* para las capas).",
        "     Generado por tools/mapa.py -- no editar a mano.",
        "     ===================================================================== -->",
        cabecera,
        css,
        html,
        js,
        "",
    ]
    salida = "\n".join(partes)

    problemas = revisa(salida)
    print("  %-34s %s" % ("mapa-embed-hostinger.html", "OK" if not problemas else "PROBLEMAS"))
    for p in problemas:
        print("      · %s" % p)
    if problemas:
        return 1

    open(SALIDA, "w", encoding="utf-8").write(salida)
    print("  escrito: %s  (%d KB)" % (os.path.relpath(SALIDA, RAIZ),
                                      len(salida.encode("utf-8")) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
