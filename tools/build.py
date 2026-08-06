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
   MOVIL: un telefono por caso, que se "activa" al entrar en pantalla.
   El anclaje por JS siempre va un fotograma por detras del scroll y eso se
   percibe como temblor. Aqui no hay nada anclado: cada caso lleva SU propio
   telefono al lado, y la animacion es que crece y se enciende al asomar.
   Es una transicion CSS disparada por una clase, asi que corre en el
   compositor y no puede temblar. El telefono suelto de arriba desaparece:
   sobraba, y era el que se veia separado de las imagenes.
   -------------------------------------------------------------------- */
@media(max-width:760px){
  #hbp .story-layout{display:block;position:relative}
  #hbp .phone-rail{display:none!important}   /* el teléfono por fila lo sustituye */
  #hbp .story-steps{padding-top:0!important;position:relative;z-index:2}
  #hbp .story-step{min-height:0;background:none;align-content:start;
    grid-template-columns:132px minmax(0,1fr);gap:18px;padding:34px 4px;align-items:start}
  #hbp .story-step .step-no{grid-column:1;grid-row:1;padding-top:0;text-align:center}
  #hbp .story-step>div{grid-column:2;grid-row:1/3}
  #hbp .story-step h3{font-size:clamp(1.85rem,8vw,2.7rem);max-width:none}
  #hbp .story-step p{font-size:.95rem}
  #hbp .story-step ul{margin-top:18px}

  /* El teléfono de la fila: marco propio con su captura dentro. */
  #hbp .story-step::before{content:'';grid-column:1;grid-row:2;width:132px;height:236px;
    border-radius:19px;padding:4px;
    background-color:#0a0a0f;background-clip:content-box;
    background-size:cover;background-position:top center;background-repeat:no-repeat;
    box-shadow:0 0 0 2px rgba(255,255,255,.24),0 16px 34px rgba(0,0,0,.55);
    transform:scale(.68);opacity:.3;
    transition:transform .8s cubic-bezier(.16,1,.3,1),opacity .6s ease,box-shadow .8s ease}
  /* "Encendido": crece y toma color al entrar en pantalla. */
  #hbp .story-step.mv-activo::before{transform:scale(1);opacity:1;
    box-shadow:0 0 0 2px rgba(255,255,255,.34),0 22px 46px rgba(0,0,0,.62),
               0 0 34px rgba(90,43,255,.34)}
  #hbp .story-step:nth-child(1)::before{background-image:var(--miniatura-1)}
  #hbp .story-step:nth-child(2)::before{background-image:var(--miniatura-2)}
  #hbp .story-step:nth-child(3)::before{background-image:var(--miniatura-3)}
  #hbp .story-step:nth-child(4)::before{background-image:var(--miniatura-4)}

  /* Alterna el lado en las filas pares. */
  #hbp .story-step:nth-child(even){grid-template-columns:minmax(0,1fr) 132px}
  #hbp .story-step:nth-child(even) .step-no{grid-column:2}
  #hbp .story-step:nth-child(even)>div{grid-column:1}
  #hbp .story-step:nth-child(even)::before{grid-column:2;grid-row:2}
}
@media(max-width:480px){
  #hbp .story-step{grid-template-columns:112px minmax(0,1fr);gap:14px;padding-inline:2px}
  #hbp .story-step:nth-child(even){grid-template-columns:minmax(0,1fr) 112px}
  #hbp .story-step::before{width:112px;height:200px}
}
</style>""", 1)

    # Las capturas de cada telefono salen de las mismas imagenes del carrusel:
    # se declaran como variables CSS para no duplicar URLs a mano.
    _slides = re.findall(r'<figure class="story-slide[^"]*"[^>]*>\s*<img src="([^"]+)"', src)
    assert len(_slides) >= 4, 'no se encontraron las 4 capturas del carrusel'
    _vars = ''.join('  --miniatura-%d:url(%s);\n' % (i + 1, u) for i, u in enumerate(_slides[:4]))
    src = src.replace('</style>', '@media(max-width:760px){#hbp{\n' + _vars + '}}\n</style>', 1)
    # Una sola declaracion (el otro uso es el var() que la lee).
    assert src.count('--miniatura-1:') == 1, 'las miniaturas se declararon dos veces'

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
/* Solo la pantalla del telefono se aisla. En .phone-stage NO se puede:
   contain:paint recorta lo que sobresale, y la tarjeta con el nombre del
   proyecto sobresale a proposito -- se veia cortada. */
#hbp .story-slides{contain:paint}
/* Dentro del iframe el boton propio no puede ser flotante (el iframe mide lo
   que su contenido, asi que position:fixed queda anclado al documento). El
   runtime global crea el real fuera; aqui se oculta para no duplicarlo. */
#hbp.hb-en-marco .wa-float{display:none!important}
/* Las entradas duran menos y recorren menos distancia. Animar opacidad sobre
   un panel con backdrop-filter obliga a recomponer el desenfoque en cada
   fotograma de la transicion: menos fotogramas, menos picos. Y mientras el
   bloque aun no es visible no hay nada que desenfocar, asi que se apaga. */
#hbp.motion-ready .reveal{transform:translateY(20px);
  transition:opacity .55s var(--ease),transform .55s var(--ease)}
#hbp.motion-ready .reveal:not(.is-visible){backdrop-filter:none;-webkit-backdrop-filter:none}
/* --- Desenfoque en reposo, desenfoque barato en movimiento ---
   El coste de backdrop-filter esta en el RADIO, y se paga en cada fotograma
   en que cambia lo que hay detras del panel: es decir, todo el rato mientras
   se hace scroll. Medido en la seccion social, a 1440x900: con 12px se
   pierden ~3 fotogramas cada segundo y medio de desplazamiento; con 4px, 0.
   Asi que mientras la pagina se mueve el radio baja a 4px y al detenerse
   recupera los 12px. No se quita del todo a proposito: la tarjeta con el
   nombre del proyecto va encima de la captura y su texto tiene que seguir
   leyendose. En movimiento la diferencia no se distingue; quieto, que es
   cuando se mira de verdad, el cristal esta intacto.
   El motor pone y quita .hb-moviendo segun si el desplazamiento cambia. */
#hbp.hb-moviendo .liquid{backdrop-filter:blur(4px) saturate(150%);
  -webkit-backdrop-filter:blur(4px) saturate(150%)}
#hbp.hb-moviendo .nav{backdrop-filter:blur(4px) saturate(140%);
  -webkit-backdrop-filter:blur(4px) saturate(140%)}
#hbp.hb-moviendo .division-pill,#hbp.hb-moviendo .mobile-menu{
  backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)}
/* --- En la seccion animada, ningun cristal desenfoca ---
   Es la seccion que se mueve por transform en cada fotograma, y ahi el
   backdrop-filter da dos problemas a la vez:
     - Coste: hay que releer y desenfocar el fondo en cada fotograma, porque
       el fondo cambia en cada fotograma. Son los cuatro paneles de texto mas
       la tarjeta del proyecto.
     - Artefacto: un panel con backdrop-filter DENTRO de una capa
       transformada lee el fondo en un espacio distinto al desplazamiento
       subpixel de la capa. En Chromium eso se ve como un temblor del
       contenido desenfocado respecto al borde del panel -- exactamente el
       "vibra un poco el movil al hacer scroll". Al ser un artefacto de
       render y no solo un coste, reducir el radio no lo arregla: hay que
       dejar de muestrear el fondo.
   Quitarlo aqui no cambia nada de lo que se ve: comparadas las capturas con
   y sin desenfoque son identicas, porque el fondo de esta seccion es oscuro y
   casi uniforme y desenfocar algo uniforme lo deja igual. Lo que da el efecto
   de cristal es el degradado propio del panel, el borde y los brillos
   interiores, que siguen intactos. La tarjeta del proyecto, que si cae sobre
   la captura del telefono, recibe ademas su propio tinte para asegurar el
   contraste del texto. */
#hbp-social .liquid,#hbp .project .liquid,
#hbp.hb-moviendo #hbp-social .liquid,#hbp.hb-moviendo .project .liquid{
  backdrop-filter:none;-webkit-backdrop-filter:none}
#hbp .phone-caption,#hbp.hb-moviendo .phone-caption{
  backdrop-filter:none;-webkit-backdrop-filter:none;
  background-color:rgba(9,9,16,.55)}
/* --- Cristales que no se estan viendo ---
   Un panel con backdrop-filter cuesta fotogramas AUNQUE este invisible: en
   Chromium mantiene vivo su backdrop root y con el la ruta de scroll caro
   para todo el documento. Medido con el menu movil cerrado (visibility:
   hidden, arriba del todo, jamas a la vista): 1.6 fotogramas perdidos por
   cada segundo y medio de desplazamiento. Apagarlo mientras esta cerrado no
   cambia nada de lo que se ve y devuelve esos fotogramas.
   Lo mismo con los cristales de la portada, que quedan muy arriba en cuanto
   se baja: el motor marca .hb-portada-lejos y ahi se apagan. */
#hbp .mobile-menu:not(.open){backdrop-filter:none;-webkit-backdrop-filter:none}
#hbp.hb-portada-lejos .hero-frame,#hbp.hb-portada-lejos .glass-stamp,
#hbp.hb-portada-lejos .division-pill,#hbp.hb-portada-lejos .nav,
#hbp.hb-moviendo.hb-portada-lejos .nav{
  backdrop-filter:none;-webkit-backdrop-filter:none}
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
