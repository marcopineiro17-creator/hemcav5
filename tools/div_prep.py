#!/usr/bin/env python3
"""Prepara el CSS de Divisiones para vivir dentro de #cpm-divisiones.

En el archivo original hay 29 selectores que se salen del contenedor: *, html,
body, .footer-links a, .metric, .signal i... Dentro del iframe publicado no se
notan, pero el editor de Hostinger inyecta el codigo EN LINEA mientras editas:
ahi ese CSS le pega a la interfaz del editor. De ahi el "se buggea hasta que
publico". Aqui se acota todo y se corrigen las alturas de viewport.
"""
import re, sys

FUENTE = '/root/.claude/uploads/9cc97cf1-cf11-5baf-bfa7-8b088d8a288d/878c7a51-codigohostinger.html'
DESTINO = '/tmp/div_css.txt'
RAIZ = '#cpm-divisiones'

css = re.search(r'<style>(.*?)</style>', open(FUENTE, encoding='utf-8').read(), re.S).group(1)

# ---------------------------------------------------------------- 1. Ediciones
E = [
 # El alto de pantalla se toma del viewport REAL (el del documento padre). Con
 # 100svh a secas se mide contra el viewport del iframe, que vale lo que mide el
 # contenido: cada pantalla se vuelve enorme y el bloque crece sin parar.
 ('--vh:100svh;', '--vh:var(--vh-real,100svh);'),
 # El contenedor pasa a ser el marco de referencia de todo lo posicionado
 # (la portada de entrada, sobre todo) y asume el recorte horizontal que antes
 # hacia body.
 ('width:100%;max-width:100%;min-height:0;margin:0;padding:0;',
  'position:relative;width:100%;max-width:100%;min-height:0;margin:0;padding:0;'),
]
for viejo, nuevo in E:
    if viejo not in css:
        sys.exit('AVISO: no se encontro -> ' + viejo[:60])
    css = css.replace(viejo, nuevo)

# ------------------------------------------------------- 2. Acotado bajo la raiz
def trozos(bloque):
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
        # html y body no existen aqui dentro: sus reglas se descartan y lo que
        # hacia falta de ellas ya vive en el contenedor.
        if t in ('html', 'body'): return None
        if t == ':root': partes.append(RAIZ)
        elif t == '*': partes.append(RAIZ + ' *')
        elif t.startswith(RAIZ): partes.append(t)
        else: partes.append(RAIZ + ' ' + t)
    return ', '.join(partes) if partes else None

AT_ANIDADAS = re.compile(r'^\s*@(media|supports|container)\b', re.I)

def acota(bloque, sangria='    '):
    res = ''
    for regla in trozos(bloque):
        # Los comentarios previos se conservan pero no deben impedir reconocer
        # un @media: ese fallo convertiria el bloque en "X @media {...}", CSS
        # invalido que el navegador descarta entero.
        coms, resto = '', regla
        while True:
            m = re.match(r'\s*(/\*.*?\*/)', resto, re.S)
            if not m: break
            coms += sangria + m.group(1).strip() + '\n'
            resto = resto[m.end():]

        if AT_ANIDADAS.match(resto):
            m = re.match(r'\s*([^{]+)\{(.*)\}\s*$', resto, re.S)
            if not m: res += coms + resto; continue
            dentro = acota(m.group(2), sangria + '  ')
            if dentro.strip():
                res += coms + sangria + m.group(1).strip() + ' {\n' + dentro + sangria + '}\n'
            continue

        # @keyframes, @font-face y demas no llevan selector: pasan tal cual.
        # Los nombres de keyframes ya son propios del bloque.
        if re.match(r'^\s*@', resto):
            res += coms + sangria + resto.strip() + '\n'
            continue

        m = re.match(r'\s*([^{]+)\{(.*)\}\s*$', resto, re.S)
        if not m:
            if resto.strip(): res += coms + resto
            continue
        ns = acota_selector(m.group(1))
        if ns is None: continue
        res += coms + sangria + ns + ' { ' + ' '.join(m.group(2).split()) + ' }\n'
    return res

acotado = acota(css)

# ------------------------------------------------------ 3. Reglas adicionales
acotado += """
    /* Nada puede quedar invisible si el JS no llega a ejecutarse. El ocultado
       de las entradas y la portada solo existen cuando el guion ya marco el
       contenedor, cosa que hace antes del primer pintado. */
    %(R)s .reveal { opacity: 1; transform: none; }
    %(R)s.js-on .reveal { opacity: 0; transform: translateY(46px); }
    %(R)s.js-on .reveal.is-visible { opacity: 1; transform: none; }
    %(R)s .intro { display: none; }
    %(R)s.js-on .intro { display: grid; }

    /* La portada se cierra sola con una animacion de CSS, no con JS. Antes
       dependia de que GSAP cargara desde un CDN externo: si tardaba o el
       navegador lo bloqueaba, la portada se quedaba tapando el bloque. */
    %(R)s.js-on .intro { animation: cpmIntroFuera .7s ease 2.5s both; }
    %(R)s.js-on .intro-logo { animation: cpmIntroLogo .9s cubic-bezier(.2,.7,.2,1) both; }
    %(R)s.js-on .intro-word { animation: cpmIntroPalabra .75s cubic-bezier(.2,.7,.2,1) .25s both; }
    @keyframes cpmIntroFuera { to { opacity: 0; visibility: hidden; } }
    @keyframes cpmIntroLogo { from { opacity: 0; transform: translateY(44px) scale(.94); } }
    @keyframes cpmIntroPalabra { from { opacity: 0; transform: translateY(-26px); letter-spacing: .18em; } }
    %(R)s .intro.is-gone { animation: none; opacity: 0; visibility: hidden; pointer-events: none; }

    /* Enlaces que salen del bloque: siempre en la ventana completa. */
    %(R)s a[target="_top"] { cursor: pointer; }

    /* El escenario de cada capitulo aisla sus repintados. */
    %(R)s .chapter { contain: paint; }

    @media (prefers-reduced-motion: reduce) {
      %(R)s.js-on .intro { display: none; }
      %(R)s.js-on .reveal { opacity: 1; transform: none; }
    }
""" % {'R': RAIZ}

# ------------------------------------------------------------- 4. Verificacion
fallos = []
def revisa(bloque):
    for regla in trozos(bloque):
        resto = regla
        while True:
            m = re.match(r'\s*(/\*.*?\*/)', resto, re.S)
            if not m: break
            resto = resto[m.end():]
        if AT_ANIDADAS.match(resto):
            m = re.match(r'\s*([^{]+)\{(.*)\}\s*$', resto, re.S)
            if m: revisa(m.group(2))
            continue
        if re.match(r'^\s*@', resto): continue          # @keyframes y demas
        m = re.match(r'\s*([^{]+)\{(.*)\}\s*$', resto, re.S)
        if not m: continue
        for sel in m.group(1).split(','):
            sel = sel.strip()
            if not sel: continue
            if '@' in sel: fallos.append('at-rule mal acotada: ' + sel[:60])
            elif not sel.startswith(RAIZ): fallos.append('selector sin acotar: ' + sel[:60])
revisa(acotado)

n_media = len(re.findall(r'@media', acotado))
print('  reglas @media conservadas :', n_media)
print('  problemas de acotado      :', fallos or 'ninguno')
if fallos or n_media < 3:
    sys.exit('CSS no valido')
open(DESTINO, 'w', encoding='utf-8').write(acotado)
print('  CSS escrito               :', round(len(acotado) / 1024), 'KB')
