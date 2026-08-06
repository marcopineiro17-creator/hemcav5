#!/usr/bin/env python3
"""Prepara el CSS de HEMCA para vivir dentro de .hemca, sin tocar el resto
de la pagina anfitriona. Reproducible: parte siempre del archivo original."""
import re, sys

FUENTE = '/home/user/hemcav5/hemca-hostinger.html'
DESTINO = '/tmp/css_embed.txt'

css = re.search(r'<style>(.*?)</style>', open(FUENTE, encoding='utf-8').read(), re.S).group(1)

# ---------------------------------------------------------------- 1. Ediciones
# Ese comentario habla de la raiz del documento, que aqui ya no existe, y su
# texto contiene etiquetas literales que rompen el troceado del archivo.
css = re.sub(r'\s*/\* El recorte horizontal.*?\*/', '', css, flags=re.S)

E = [
 # Etapas: anclaje calculado en vez de position:sticky, y alturas del viewport real.
 ('.story-layout { position: relative; min-height: 400vh; min-height: 400svh; }',
  '/* Anclaje por JS en lugar de position:sticky: dentro del iframe el\n'
  '       documento no hace scroll propio, asi que el sticky no puede aplicar.\n'
  '       La altura del bloque ES el recorrido: una pantalla por etapa. */\n'
  '    .story-layout { position: relative; height: calc(var(--vh-real, 100svh) * 4); }'),
 ('.story-stage { position: sticky; top: var(--nav-h); height: calc(100vh - var(--nav-h)); height: calc(100svh - var(--nav-h)); overflow: hidden; }',
  '.story-stage { position: absolute; top: 0; left: 0; width: 100%; height: var(--vh-real, 100svh); overflow: hidden; will-change: transform; }'),
 ('.hero { position: relative; min-height: min(900px, calc(100svh - var(--nav-h)));',
  '.hero { position: relative; min-height: clamp(560px, calc(var(--vh-real, 100svh) * .78), 880px);'),
 # El menu no es fijo: la pagina del constructor ya tiene su cabecera.
 ('.section-nav { position: sticky; z-index: 70; top: 0; height: var(--nav-h);',
  '.section-nav { position: relative; z-index: 10; height: var(--nav-h);'),
 ('section { scroll-margin-top: calc(var(--nav-h) + 8px); }', 'section { scroll-margin-top: 20px; }'),
 # Los indicadores son botones utilizables: barra de 3px con zona de clic de 21px.
 ('.chapter-dot { width: 48px; height: 3px; background: rgba(255, 255, 255, .25); transition: width .3s ease, background .3s ease; }',
  '.chapter-dot { box-sizing: content-box; width: 48px; height: 3px; padding: 9px 0; border: 0; background: rgba(255, 255, 255, .25); background-clip: content-box; cursor: pointer; transition: width .3s ease, background .3s ease; }\n'
  '    .chapter-dot:hover { background: rgba(255, 255, 255, .5); background-clip: content-box; }'),
 ('.chapter-dot.active { width: 78px; background: var(--orange); }',
  '.chapter-dot.active { width: 78px; background: var(--orange); background-clip: content-box; }'),
 ('.wa-float { position: fixed; z-index: 9999;', '.wa-float { position: fixed; z-index: 900;'),
 # Movil: el hero deja de depender de la altura de la ventana del iframe.
 ('.hero { min-height: calc(100svh - var(--nav-h)); }',
  '.hero { min-height: clamp(540px, calc(var(--vh-real, 100svh) * .86), 760px); }'),
]
for viejo, nuevo in E:
    if viejo not in css:
        print('  AVISO: no se encontro ->', viejo[:70]); continue
    css = css.replace(viejo, nuevo)

# El contenedor asume el recorte horizontal que antes hacia la raiz.
css = css.replace(':root {', ':root {\n      position: relative;\n      overflow-x: clip;\n      max-width: 100%;', 1)

# ------------------------------------------------------- 2. Acotado bajo .hemca
def trozos(bloque):
    """Parte el CSS en reglas de primer nivel, contando llaves."""
    out, prof, buf = [], 0, ''
    for ch in bloque:
        buf += ch
        if ch == '{': prof += 1
        elif ch == '}':
            prof -= 1
            if prof == 0: out.append(buf); buf = ''
    if buf.strip(): out.append(buf)
    return out

def acota_selector(sel):
    partes = []
    for uno in sel.split(','):
        t = uno.strip()
        if not t: continue
        if t == 'html': return None                      # se descarta
        if t in (':root', 'body'): partes.append('.hemca')
        elif t.startswith('.hemca'): partes.append(t)
        elif t.startswith('.js '): partes.append(t.replace('.js ', '.hemca.js-on ', 1))
        else: partes.append('.hemca ' + t)
    return ', '.join(partes) if partes else None

AT_ANIDADAS = re.compile(r'^\s*@(media|supports|container)\b', re.I)

def acota(bloque, sangria='    '):
    res = ''
    for regla in trozos(bloque):
        # Los comentarios que preceden a la regla se conservan, pero NO deben
        # impedir reconocer un @media: ese fallo convertia el bloque entero en
        # ".hemca @media {...}", CSS invalido que el navegador descarta.
        coms = ''
        resto = regla
        while True:
            m = re.match(r'\s*(/\*.*?\*/)', resto, re.S)
            if not m: break
            coms += sangria + m.group(1).strip() + '\n'
            resto = resto[m.end():]

        if AT_ANIDADAS.match(resto):
            m = re.match(r'\s*([^{]+)\{(.*)\}\s*$', resto, re.S)
            if not m: res += coms + resto; continue
            res += coms + sangria + m.group(1).strip() + ' {\n' + acota(m.group(2), sangria + '  ') + sangria + '}\n'
            continue

        m = re.match(r'\s*([^{]+)\{(.*)\}\s*$', resto, re.S)
        if not m:
            if resto.strip(): res += coms + resto
            continue
        ns = acota_selector(m.group(1))
        if ns is None: continue
        cuerpo = ' '.join(m.group(2).split())
        res += coms + sangria + ns + ' { ' + cuerpo + ' }\n'
    return res

acotado = acota(css)

# ------------------------------------------------------ 3. Reglas adicionales
acotado += """
    /* Desenfoque del menu mas barato: se recalcula al desplazarse. */
    .hemca .section-nav { backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }

    /* Y mas barato aun MIENTRAS se desplaza. El coste de backdrop-filter esta
       en el radio, y se paga en cada fotograma en que cambia lo que hay detras
       del panel: o sea, durante todo el scroll. Con el radio reducido a 4px el
       coste practicamente desaparece; al detenerse vuelve el desenfoque
       completo. En movimiento no se distingue, y quieto -- que es cuando se
       mira -- queda igual. El motor pone y quita .hb-moviendo. */
    .hemca.hb-moviendo .section-nav { backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); }

    /* Las etapas inactivas seguian pintandose y componiendose: cuatro
       imagenes a pantalla completa con filtros, en cada fotograma del
       escenario en movimiento. Con visibility se saltan por completo y solo
       queda una. Es lo que abarata la animacion en escritorio. */
    .hemca .story-image { visibility: hidden; transition: opacity .55s ease, visibility .55s ease; }
    .hemca .story-image.active { visibility: visible; }
    /* El escenario aisla sus repintados y vive en su propia capa. */
    .hemca .story-stage { contain: paint; backface-visibility: hidden; }

    /* Cuando no se puede medir el scroll (iframe de otro origen), el bloque
       no debe reservar cuatro pantallas: seria un hueco vacio. */
    .hemca.etapas-tiempo .story-layout { height: auto; }
    .hemca.etapas-tiempo .story-stage { position: relative; height: clamp(560px, 74vh, 820px); transform: none !important; }

    /* Dentro del iframe el boton propio no puede flotar de verdad: el runtime
       global de CPM crea el real fuera. Aqui se oculta para no duplicarlo. */
    .hemca.hb-en-marco .wa-float { display: none !important; }

    /* Respaldo para navegadores sin overflow:clip (Safari anterior a 16). */
    @supports not (overflow: clip) {
      .hemca { overflow-x: hidden; }
    }
"""

# ------------------------------------------------------------- 4. Verificacion
fallos = []
def revisa(bloque, dentro_de_at=False):
    for regla in trozos(bloque):
        resto = regla
        while True:
            m = re.match(r'\s*(/\*.*?\*/)', resto, re.S)
            if not m: break
            resto = resto[m.end():]
        if AT_ANIDADAS.match(resto):
            m = re.match(r'\s*([^{]+)\{(.*)\}\s*$', resto, re.S)
            if m: revisa(m.group(2), True)
            continue
        m = re.match(r'\s*([^{]+)\{(.*)\}\s*$', resto, re.S)
        if not m: continue
        for sel in m.group(1).split(','):
            sel = sel.strip()
            if not sel: continue
            if '@' in sel: fallos.append('at-rule mal acotada: ' + sel[:60])
            elif not sel.startswith('.hemca'): fallos.append('selector sin acotar: ' + sel[:60])
revisa(acotado)

n_media = len(re.findall(r'@media', acotado))
print('  reglas @media conservadas :', n_media)
print('  problemas de acotado      :', fallos or 'ninguno')
if fallos or n_media < 3:
    sys.exit('CSS no valido')
open(DESTINO, 'w', encoding='utf-8').write(acotado)
print('  CSS escrito               :', round(len(acotado)/1024), 'KB')
