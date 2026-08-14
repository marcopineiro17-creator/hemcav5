#!/usr/bin/env python3
"""Construye el bloque de Regularizacion de Predios para el contenedor de
codigo de Hostinger.

A diferencia de los otros bloques, este no parte de un original pegado: se
escribe aqui, en tres piezas (CSS, maquetacion y guion), y este programa las
une con el motor de scroll compartido y las revisa antes de publicar.
"""
import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SALIDA = os.path.join(RAIZ, "predios-embed-hostinger.html")
CONTENEDOR = "cpm-predios"


def lee(nombre):
    return open(os.path.join(AQUI, nombre), encoding="utf-8").read().strip()


def inserta_motor(js):
    motor = lee("hb-engine.js")
    ind = "\n".join(("    " + l) if l.strip() else l for l in motor.split("\n"))
    out = js.replace("/*__MOTOR__*/", ind)
    assert "__MOTOR__" not in out, "no se sustituyo el hueco del motor"
    assert "function hbEngine" in out, "el motor no quedo dentro del guion"
    return out


def sin_comentarios(s):
    """Quita comentarios CSS y HTML. Las revisiones se hacen sobre esto:
    los propios comentarios explican los problemas y mencionan las cadenas
    que se persiguen, y sin esto se delatarian a si mismos."""
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)


def quita_keyframes(css):
    """Saca los bloques @keyframes enteros antes de revisar el acotado.

    Dentro de un @keyframes los 'selectores' son `from`, `to` y porcentajes,
    que por definicion no llevan el id del contenedor. Sin quitarlos, la
    revision los denuncia como CSS suelto -- que es justo el falso positivo
    que ya habia costado tiempo en otro guion del repositorio.
    """
    fuera, i = [], 0
    while True:
        m = re.search(r"@keyframes[^{]*\{", css[i:])
        if not m:
            fuera.append(css[i:])
            break
        ini = i + m.start()
        fuera.append(css[i:ini])
        # Contar llaves para encontrar el cierre del bloque completo.
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

    # 1. Sintaxis de cada guion. Un error aqui no da error visible: el motor
    #    simplemente no arranca y el bloque se queda sin animaciones.
    for i, js in enumerate(re.findall(r"<script>(.*?)</script>", s, re.S)):
        f = os.path.join(tempfile.gettempdir(), "chk_predios_%d.js" % i)
        open(f, "w", encoding="utf-8").write(js)
        r = subprocess.run(["node", "--check", f], capture_output=True, text=True)
        if r.returncode:
            linea = (r.stderr.split("\n") + ["", "", ""])[2].strip()[:80]
            problemas.append("guion %d invalido: %s" % (i, linea))

    # 2. Etiquetas de documento: esto va DENTRO de otra pagina.
    #    Ojo: '<head' tambien casa con '<header>', asi que la maquetacion
    #    no puede usar esa etiqueta. Es a proposito.
    for t in ["<!doctype", "<html", "<head", "<body"]:
        if t in bajo:
            problemas.append("contiene " + t)

    # 3. Etiquetas desparejadas.
    if s.count("<style>") != s.count("</style>"):
        problemas.append("etiquetas <style> desparejadas")
    if s.count("<script") != s.count("</script>"):
        problemas.append("etiquetas <script> desparejadas")

    # 4. Nada de CDN ni dependencias externas.
    for mal in ["cdnjs", "cdn.jsdelivr", "unpkg", "googleapis", "gsap"]:
        if mal in bajo:
            problemas.append("dependencia externa: " + mal)

    # 5. Alturas de viewport sin acotar: realimentan dentro del iframe
    #    (mas alto -> svh mayor -> mas alto) y producen la franja blanca.
    for m in re.finditer(r"[:\s(]([0-9.]+)(svh|vh)\b", limpio):
        ctx = limpio[max(0, m.start() - 60):m.start()]
        if "vh-real" in ctx or "clamp(" in ctx:
            continue
        problemas.append("altura de viewport sin acotar: " + m.group(0).strip())

    # 6. Todo el CSS acotado al contenedor. Un selector suelto le cambia el
    #    aspecto al editor del constructor y al resto del sitio.
    css = "\n".join(re.findall(r"<style>(.*?)</style>", s, re.S))
    css = sin_comentarios(css)
    css = quita_keyframes(css)
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
            if not parte.startswith("#" + CONTENEDOR):
                sueltos.append(parte[:60])
    if sueltos:
        problemas.append("%d selectores fuera del contenedor: %s"
                         % (len(sueltos), "; ".join(sueltos[:4])))

    # 7. Ningun enlace relativo: dentro del iframe navegan por dentro.
    for m in re.finditer(r'href="(/[^/][^"]*)"', s):
        problemas.append("enlace relativo: " + m.group(1))

    return problemas


def main():
    css = lee("predios_css.txt")
    html = lee("predios_html.txt")
    js = inserta_motor(lee("predios_js.txt"))
    cabecera = lee("cabecera.js")

    partes = [
        "<!-- =====================================================================",
        "     CPM · REGULARIZACION DE PREDIOS",
        "     Bloque para el contenedor de codigo de Hostinger.",
        "     Se pega tal cual: no lleva etiquetas de documento, todo su CSS esta",
        "     acotado a #cpm-predios y no depende de ningun CDN.",
        "     Generado por tools/predios.py -- no editar a mano.",
        "     ===================================================================== -->",
        cabecera,
        css,
        html,
        js,
        "",
    ]
    salida = "\n".join(partes)

    problemas = revisa(salida)
    print("  %-36s %s" % ("predios-embed-hostinger.html",
                          "OK" if not problemas else "PROBLEMAS"))
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
