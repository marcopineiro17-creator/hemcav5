#!/usr/bin/env python3
"""Construye los dos bloques para el contenedor de codigo de Hostinger."""
import re, sys, subprocess, tempfile, os

MOTOR = open('/tmp/hb-engine.js', encoding='utf-8').read().strip()
TEMPRANO = open('/tmp/temprano.js', encoding='utf-8').read().strip()
CABECERA = open('/tmp/cabecera.js', encoding='utf-8').read().strip()

def inserta_motor(js):
    ind = '\n'.join(('    ' + l) if l.strip() else l for l in MOTOR.split('\n'))
    out = js.replace('/*__MOTOR__*/', ind)
    assert '__MOTOR__' not in out and 'function hbEngine' in out
    return out

def revisa(nombre, s):
    bajo = s.lower()
    problemas = []
    # Sintaxis de cada bloque de script. Un error aqui no da error visible en
    # la pagina: el motor simplemente no arranca y las animaciones no existen.
    for i, js in enumerate(re.findall(r'<script>(.*?)</script>', s, re.S)):
        f = os.path.join(tempfile.gettempdir(), 'chk_%s_%d.js' % (nombre.split('.')[0], i))
        open(f, 'w', encoding='utf-8').write(js)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
        if r.returncode:
            problemas.append('JS invalido en el bloque %d: %s' % (i, r.stderr.split(chr(10))[2].strip()[:70]))
    if s.count('<style>') != s.count('</style>'): problemas.append('etiquetas <style> desparejadas')
    if s.count('<script') != s.count('</script>'): problemas.append('etiquetas <script> desparejadas')
    for t in ['<!doctype', '<html', '<head', '<body']:
        if t in bajo: problemas.append('contiene ' + t)
    # Unidades de altura de viewport sin acotar: causan realimentacion en el
    # iframe. Se revisa sobre el codigo SIN comentarios, porque los propios
    # comentarios mencionan 100svh al explicar el problema.
    limpio = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    limpio = re.sub(r'<!--.*?-->', '', limpio, flags=re.S)
    for m in re.finditer(r'[:\s(]([0-9.]+)(svh|vh)\b', limpio):
        ctx = limpio[max(0, m.start()-60):m.start()]
        if 'vh-real' in ctx or 'clamp(' in ctx: continue
        problemas.append('altura de viewport sin acotar: ' + m.group(0).strip())
    print(('  %-34s' % nombre), 'OK' if not problemas else 'PROBLEMAS: ' + '; '.join(problemas))
    return not problemas

# ------------------------------------------------------------------ HEMCA
def hemca():
    src = open('/home/user/hemcav5/hemca-hostinger.html', encoding='utf-8').read()
    css = re.sub(r'\s*/\* El recorte horizontal.*?\*/', '',
                 open('/tmp/css_embed.txt', encoding='utf-8').read(), flags=re.S)
    cuerpo = src.split('</head>', 1)[1].split('<body>', 1)[1].rsplit('</body>', 1)[0]
    assert '<style' not in cuerpo and 'overflow-x' not in cuerpo
    cuerpo = re.sub(r'\s*<div class="progress"[^>]*></div>\n', '\n', cuerpo)
    cuerpo = re.sub(r'\s*<script>.*?</script>\s*$', '', cuerpo, flags=re.S)
    cuerpo = cuerpo.replace('<main>', '<div class="hemca-main">').replace('</main>', '</div>')

    viejo = re.search(r'<div class="story-chapters"[^>]*>.*?</div>', cuerpo, re.S).group(0)
    nuevo = ('<div class="story-chapters" role="tablist" aria-label="Etapas del método">\n'
             + '\n'.join('          <button class="chapter-dot%s" type="button" role="tab" '
                         'aria-selected="%s" aria-controls="etapa-%d" aria-label="Ir a la etapa %02d"></button>'
                         % (' active' if i == 0 else '', 'true' if i == 0 else 'false', i, i + 1)
                         for i in range(4)) + '\n        </div>')
    cuerpo = cuerpo.replace(viejo, nuevo)
    for i in range(4):
        cuerpo = cuerpo.replace('<article class="story-card%s" data-story="%d">' % (' active' if i == 0 else '', i),
                                '<article class="story-card%s" data-story="%d" id="etapa-%d" role="tabpanel">'
                                % (' active' if i == 0 else '', i, i))

    fuente = ("@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800"
              "&family=Manrope:wght@400;600;700;800&display=swap');")
    jsonld = re.search(r'<script type="application/ld\+json">.*?</script>', src, re.S).group(0)
    js = inserta_motor(open('/tmp/embed_js.txt', encoding='utf-8').read().strip())

    out = (CABECERA + '\n'
           '<!-- HEMCA | bloque para el contenedor de codigo de Hostinger.\n'
           '     Todo el CSS esta acotado bajo .hemca para no afectar al resto de la pagina.\n'
           '     No lleva etiquetas de documento: se pega tal cual en el bloque de codigo. -->\n'
           '<style>\n' + fuente + '\n' + css + '\n</style>\n\n<div class="hemca">\n'
           + TEMPRANO.replace('if (!r) return;', 'if (!r) return;\n  r.classList.add("js-on");') + '\n'
           + cuerpo.strip() + '\n' + jsonld + '\n</div>\n' + js + '\n')
    open('/home/user/hemcav5/hemca-embed-hostinger.html', 'w', encoding='utf-8').write(out)
    return revisa('hemca-embed-hostinger.html', out)

# -------------------------------------------------------------- PORTAFOLIO
def portafolio():
    src = open('/root/.claude/uploads/9cc97cf1-cf11-5baf-bfa7-8b088d8a288d/'
               'a8c30d08-portafoliohmshostinger.html', encoding='utf-8').read()

    src = src.replace("""  Animación: GSAP + ScrollTrigger en página directa; motor seguro basado en las
  coordenadas del viewport padre cuando Hostinger encapsula el bloque en un iframe.
  Seguridad: sin JavaScript, sin CDN o con prefers-reduced-motion, todo el contenido
  permanece visible y el portafolio continúa siendo navegable.""",
"""  Animación: motor propio, sin librerías externas. Hostinger encapsula el bloque en
  un iframe; si ese iframe mide menos que su contenido, nada de lo que quede por
  debajo de su caja llega a "entrar a vista" y el sitio se queda con el fondo y sin
  contenido. El motor le fija al iframe la altura de su propio contenido, mide contra
  el viewport de la página padre y escucha también el scroll del padre.
  Seguridad: sin JavaScript, con un error, con el padre ilegible (otro origen) o con
  prefers-reduced-motion, todo el contenido permanece visible y navegable.""")

    src = src.replace('<link rel="preconnect" href="https://cdnjs.cloudflare.com"/>\n', '')
    src = re.sub(r'\s*<script src="https://cdnjs\.cloudflare\.com/ajax/libs/gsap[^"]*"></script>', '', src)

    # Alturas de pantalla -> viewport real (dentro del iframe, svh se dispara)
    src = src.replace('calc(100svh - var(--navh) - 20px)', 'calc(var(--vh-real, 100svh) - var(--navh) - 20px)')
    src = src.replace('calc(100svh - var(--navh) - 16px)', 'calc(var(--vh-real, 100svh) - var(--navh) - 16px)')
    src = src.replace('calc(100svh - var(--navh))',        'calc(var(--vh-real, 100svh) - var(--navh))')
    src = src.replace('min-height:92svh',                  'min-height:calc(var(--vh-real, 100svh) * .92)')
    src = src.replace('min-height:78vh;',                  'min-height:calc(var(--vh-real, 100svh) * .78);')

    # .reveal necesita su propia transicion: antes la animaba GSAP
    src = src.replace('#hbp.motion-ready .reveal{opacity:0;transform:translateY(34px)}',
                      '#hbp.motion-ready .reveal{opacity:0;transform:translateY(34px);\n'
                      '  transition:opacity .9s var(--ease),transform .9s var(--ease)}')

    # El telefono se ancla por JS: el sticky no aplica dentro del iframe
    src = src.replace('#hbp .phone-stage{position:sticky;top:calc(var(--navh) + 36px);',
                      '#hbp .phone-stage{position:relative;top:auto;will-change:transform;')
    src = src.replace('#hbp.frame-mode .phone-stage{position:relative;top:auto}', '')

    src = src.replace('</style>', """
/* Sin scroll medible (iframe de otro origen): sin recorridos largos ni
   desplazamientos calculados; el contenido se muestra tal cual. */
#hbp.sin-scroll .story-step{min-height:0!important}
#hbp.sin-scroll .story-steps{padding-top:0!important}
#hbp.sin-scroll .phone-stage{transform:none!important}
</style>""", 1)


    src = src.replace('</style>', """
/* --------------------------------------------------------------------
   MOVIL: el telefono anclado y CENTRADO, a buen tamano, por encima del
   texto. Pequeno y a un lado casi no se notaba; en el flujo te lo pasabas
   y no veias el cambio. El texto corre por detras: el telefono manda en el
   z-index, asi que siempre se ve cambiar.
   -------------------------------------------------------------------- */
@media(max-width:760px){
  #hbp .story-layout{display:block;position:relative}
  #hbp .phone-rail{position:absolute!important;inset:0;min-height:0;
    pointer-events:none;z-index:6;display:block}
  #hbp .phone-stage{position:relative!important;top:auto!important;min-height:0;
    padding:0;display:flex;justify-content:center;align-items:flex-start}
  #hbp .phone{width:min(230px,62vw)}
  #hbp .phone-aura{width:300px;height:300px;opacity:.42}
  #hbp .phone-caption{position:absolute;left:50%;right:auto;top:auto;bottom:-14px;
    transform:translateX(-50%);min-width:0;white-space:nowrap;padding:9px 14px}
  /* Los capitulos empiezan bajo el telefono y su fondo solo se vuelve opaco
     en la parte baja, para no borrarlo cuando pasan por detras. */
  #hbp .story-steps{padding-top:calc(var(--vh-real, 100svh) * .6)!important;position:relative;z-index:2}
  #hbp .story-step{min-height:calc(var(--vh-real, 100svh) * .66);align-content:end;
    padding:44px 6px 40px;
    background:linear-gradient(transparent,rgba(7,7,12,.5) 32%,rgba(7,7,12,.9) 60%,rgba(7,7,12,.99))}
  #hbp .story-step h3{font-size:clamp(2rem,9vw,3rem);max-width:none}
  #hbp .story-step p{font-size:.95rem}
}
@media(max-width:480px){
  #hbp .phone{width:min(206px,60vw)}
  #hbp .story-step{grid-template-columns:30px 1fr;gap:11px;padding-inline:2px}
}
</style>""", 1)

    # El guion temprano va justo despues de abrir el contenedor.
    src = src.replace('<div id="hbp">', '<div id="hbp">\n' + TEMPRANO, 1)
    src = CABECERA + '\n' + src
    assert '--vh-real' in src.split('<style>')[0], 'el guion temprano no quedo antes del CSS'

    # -------- Coste de pintado. Se anade al final para que gane siempre. -----
    OPTIM = """
/* --------------------------------------------------------------------
   COSTE DE PINTADO
   Medido con muestreo de fotogramas durante el scroll: la seccion social
   daba una mediana de 50-66ms por fotograma en escritorio. Lo que domina
   son los desenfoques, que se recalculan cada vez que algo se mueve
   encima o debajo. El radio es lo que cuesta, no el hecho de desenfocar.
   -------------------------------------------------------------------- */
#hbp .media{contain:paint}
#hbp .ambient,#hbp .ambient .orb{will-change:auto;contain:paint}
#hbp .orb{filter:blur(80px)}
#hbp .phone-aura{filter:blur(46px)}
#hbp .liquid{backdrop-filter:blur(12px) saturate(150%);-webkit-backdrop-filter:blur(12px) saturate(150%)}
#hbp .nav{backdrop-filter:blur(12px) saturate(140%);-webkit-backdrop-filter:blur(12px) saturate(140%)}
/* El teléfono y su pantalla viven en su propia capa: al desplazarse no
   obligan a repintar el fondo de la seccion. */
#hbp .phone-stage{contain:paint}
#hbp .story-slides{contain:paint}
/* Las entradas duran menos y recorren menos distancia. Animar opacidad sobre
   un panel con backdrop-filter obliga a recomponer el desenfoque en cada
   fotograma de la transicion: menos fotogramas, menos picos. Y mientras el
   bloque aun no es visible no hay nada que desenfocar, asi que se apaga. */
#hbp.motion-ready .reveal{transform:translateY(20px);
  transition:opacity .55s var(--ease),transform .55s var(--ease)}
#hbp.motion-ready .reveal:not(.is-visible){backdrop-filter:none;-webkit-backdrop-filter:none}
"""
    src = src.replace('</style>', OPTIM + '</style>', 1)
    assert 'contain:paint' in src, 'no se aplico el bloque de coste de pintado'

    js = inserta_motor(open('/tmp/portfolio_js.txt', encoding='utf-8').read().strip())
    src = re.sub(r"<script>\n\(function\(\)\{\n  'use strict';.*?</script>", js, src, flags=re.S)

    assert 'hbEngine' in src, 'no se inserto el motor'
    assert 'gsap' not in src.lower(), 'quedan restos de gsap'
    assert 'cdnjs' not in src, 'queda el CDN'
    open('/home/user/hemcav5/portafolio-hms-embed.html', 'w', encoding='utf-8').write(src)
    return revisa('portafolio-hms-embed.html', src)

print('Construyendo:')
ok = hemca() and portafolio()
sys.exit(0 if ok else 1)
