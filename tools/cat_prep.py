#!/usr/bin/env python3
"""Repara el catalogo de propiedades de CPM. Parte siempre del original."""
import re, sys, subprocess, tempfile, os

FUENTE  = '/home/user/hemcav5/src/cpm-catalogo-original.html'
DESTINO = '/home/user/hemcav5/catalogo-embed-hostinger.html'

src = open(FUENTE, encoding='utf-8').read()
def cambia(viejo, nuevo, que):
    global src
    if viejo not in src:
        sys.exit('no se encontro: ' + que)
    src = src.replace(viejo, nuevo, 1)

# ══════════════════════════════════════════════════════════════════════
# 1. EL HUECO EN BLANCO AL FILTRAR
#    El constructor RESERVA la altura del bloque en los contenedores que
#    envuelven al iframe: alto fijo en .grid-embed, min-height en la seccion
#    y -- el que de verdad manda -- una fila de rejilla de alto fijo en
#    .block-layout. Al filtrar, el iframe encoge pero esa reserva no.
#    Medido con la estructura real: iframe 772px, seccion 5182px, 4410px de
#    blanco. El codigo que habia solo escribia height/minHeight SIN
#    prioridad y nunca tocaba grid-template-rows, asi que no ganaba.
# ══════════════════════════════════════════════════════════════════════
cambia("""    var el=FRAME.el.parentElement, n=0;
    while(el && el.tagName!=='BODY' && n<6){
      var s=el.style;
      s.height='auto'; s.minHeight='0'; s.maxHeight='none'; s.overflow='visible';
      el=el.parentElement; n++;
    }
  }catch(e){}
}""",
"""    colapsarContenedores(FRAME.el);
  }catch(e){}
}
/* ─────────────────────────────────────────────────────────
   COLAPSAR LA ALTURA RESERVADA POR EL CONSTRUCTOR
   Hostinger mide el bloque una vez y guarda esa altura en los contenedores
   del iframe. Al filtrar, el iframe encoge pero la reserva se queda: de ahi
   el hueco en blanco antes del pie. Medido: iframe 772px, seccion 5182px,
   4410px de blanco.
   Dos cosas hay que hacer, y antes no se hacia ninguna:
     · escribir con !important, porque la reserva del constructor tambien lo
       lleva y sin prioridad no se le gana;
     · poner grid-template-rows:auto en .block-layout, que es una fila de
       rejilla de alto fijo -- el min-height de la seccion por si solo no
       explica el hueco, la fila si.
   Es el mismo tratamiento que el codigo global de CPM aplica a los bloques
   que si reconoce (aqui el id no esta en su lista).
   ───────────────────────────────────────────────────────── */
function colapsarContenedores(marco){
  var el=marco.parentElement, n=0;
  while(el && el.tagName!=='BODY' && n<8){
    var s=el.style, cl=' '+(el.className||'')+' ';
    s.setProperty('height','auto','important');
    s.setProperty('min-height','0','important');
    s.setProperty('max-height','none','important');
    s.overflow='visible';
    /* La fila de rejilla: se fuerza en .block-layout y en cualquier
       contenedor que este maquetando como rejilla. */
    var esRejilla=false;
    try{ esRejilla=getComputedStyle(el).display.indexOf('grid')>=0; }catch(e){}
    if(esRejilla || cl.indexOf(' block-layout ')>=0){
      s.setProperty('grid-template-rows','auto','important');
    }
    /* El relleno de abajo solo se quita en los contenedores propios del
       bloque de codigo; en el resto podria ser separacion legitima. */
    if(/ (grid-embed|layout-element|block-layout|block) /.test(cl)){
      s.setProperty('margin-bottom','0','important');
      s.setProperty('padding-bottom','0','important');
    }
    el=el.parentElement; n++;
  }
}""", 'el bucle de contenedores en aplicarAlto')

# ══════════════════════════════════════════════════════════════════════
# 2. EN MOVIL NO APARECE EL BOTON DE CERRAR
#    La ficha se ancla a la parte visible del iframe, pero esa parte se
#    calculaba desde el borde de la ventana (0), sin descontar la cabecera
#    FIJA del sitio. Medido en movil: el boton quedaba entre 7 y 41px de
#    alto, y la cabecera del sitio ocupa los primeros 64 -- justo encima.
#    Ademas medirCabecera() miraba document.body, que dentro del iframe es
#    el del PROPIO bloque: ahi no hay ninguna cabecera fija, asi que
#    siempre media 0 y la barra de filtros tambien se escondia debajo.
# ══════════════════════════════════════════════════════════════════════
cambia("""function medirCabecera(){
  var alto=0;
  try{
    var nodos=document.body ? document.body.children : [];
    for(var i=0;i<nodos.length;i++){
      var e=nodos[i];
      if(e===root || e===portal || (e.contains && e.contains(root))) continue;
      var cs=getComputedStyle(e);
      if(cs.position!=='fixed' && cs.position!=='sticky') continue;
      if(cs.display==='none' || cs.visibility==='hidden') continue;
      var r=e.getBoundingClientRect();
      if(r.top<=2 && r.bottom>alto && r.bottom<260 && r.width>window.innerWidth*0.5) alto=r.bottom;
    }
  }catch(e){}
  root.style.setProperty('--topbar', Math.round(alto)+'px');
}""",
"""var CABECERA=0;   /* alto de la cabecera fija del sitio, en px */
/* Se mide en el documento del SITIO, no en el del bloque. Antes se miraba
   document.body, que dentro del iframe es el del propio bloque: ahi no hay
   ninguna cabecera fija, asi que el valor era siempre 0. Por eso la barra de
   filtros se escondia debajo de la cabecera y, sobre todo, por eso la ficha
   se abria con su boton de cerrar tapado. */
function ventanaSitio(){
  try{ if(FRAME && FRAME.win) return FRAME.win; }catch(e){}
  return window;
}
function documentoSitio(){
  try{ var w=ventanaSitio(); if(w && w.document) return w.document; }catch(e){}
  return document;
}
function medirCabecera(){
  var alto=0;
  try{
    var w=ventanaSitio(), doc=documentoSitio();
    var nodos=doc.body ? doc.body.children : [];
    var anchoVentana=w.innerWidth||window.innerWidth||360;
    for(var i=0;i<nodos.length;i++){
      var e=nodos[i];
      if(e===root || e===portal || (e.contains && e.contains(root))) continue;
      var cs=w.getComputedStyle ? w.getComputedStyle(e) : getComputedStyle(e);
      if(cs.position!=='fixed' && cs.position!=='sticky') continue;
      if(cs.display==='none' || cs.visibility==='hidden') continue;
      var r=e.getBoundingClientRect();
      if(r.top<=2 && r.bottom>alto && r.bottom<260 && r.width>anchoVentana*0.5) alto=r.bottom;
    }
  }catch(e){}
  CABECERA=Math.round(alto);
  /* El desplazamiento de la barra sticky SOLO se aplica fuera de un iframe.
     Dentro, el documento del bloque no hace scroll propio, asi que
     position:sticky no puede pegarse a nada: lo unico que consigue top es
     bajar la barra 64px y taparle 34px a la primera fila de tarjetas.
     Medido: barra acabando en 137px y tarjetas empezando en 103px.
     CABECERA se sigue usando para anclar la ficha, que es donde hace falta. */
  var desfase = 0;
  try{ desfase = (FRAME && FRAME.el) ? 0 : CABECERA; }catch(e){ desfase = 0; }
  root.style.setProperty('--topbar', desfase+'px');
}""", 'medirCabecera')

cambia("""function banda(){
  if(!FRAME.el) return null;
  try{
    var r=FRAME.el.getBoundingClientRect(), ph=FRAME.win.innerHeight;
    var top=Math.max(0,-r.top), bot=Math.min(r.height, ph-r.top);
    return {top:top, height:Math.max(220,bot-top)};
  }catch(e){ return null; }
}""",
"""function banda(){
  if(!FRAME.el) return null;
  try{
    var r=FRAME.el.getBoundingClientRect(), ph=FRAME.win.innerHeight;
    var bot=Math.min(r.height, ph-r.top);
    /* La banda empieza DEBAJO de la cabecera fija del sitio. Si empezara en
       el borde de la ventana, la cabecera de la ficha -- que es donde vive el
       boton de cerrar -- quedaria tapada por ella y no habria forma de cerrar
       la tarjeta. Medido en movil: el boton caia entre 7 y 41px y la cabecera
       del sitio ocupa los primeros 64. */
    var top=Math.max(0, CABECERA-r.top);
    /* Si descontar la cabecera deja una banda demasiado corta para la ficha,
       se prefiere mostrarla entera aunque roce la cabecera. */
    if(bot-top<300) top=Math.max(0,-r.top);
    return {top:top, height:Math.max(220,bot-top)};
  }catch(e){ return null; }
}""", 'banda')

# La cabecera hay que medirla antes de anclar la ficha, no solo al desplazarse.
cambia("""  var ov=$('cpmOv'); ov.classList.add('on'); seguir(ov,true);
  document.body.style.overflow='hidden';""",
"""  medirCabecera();          /* la ficha se ancla debajo de la cabecera del sitio */
  var ov=$('cpmOv'); ov.classList.add('on'); seguir(ov,true);
  document.body.style.overflow='hidden';""", 'apertura de la ficha')

# ══════════════════════════════════════════════════════════════════════
# 3. FUERA LA PORTADA: el sitio ya tiene su titulo y su logo
# ══════════════════════════════════════════════════════════════════════
m = re.search(r'\n<!-- PORTADA -->\n<div class="cpm-hero">.*?\n</div>\n', src, re.S)
if not m:
    sys.exit('no se encontro la portada')
src = src.replace(m.group(0), '\n', 1)

# Y su CSS, que ya no lo usa nadie. Se borra el tramo completo entre el
# banderin de PORTADA y el siguiente banderin: ahi dentro solo hay reglas de
# .cpm-hero y .cpm-in, que no se usan en ningun otro sitio.
ini = src.find('   PORTADA\n')
if ini < 0:
    sys.exit('no se encontro el banderin de la portada en el CSS')
ini = src.rfind('/* ', 0, ini)
fin = src.find('/* ═', ini + 3)
if fin < 0:
    sys.exit('no se encontro el final del CSS de la portada')
tramo = src[ini:fin]
sobran = [x for x in re.findall(r'^#cpm-catalogo ([^{,]+)', tramo, re.M)
          if 'cpm-hero' not in x and 'cpm-in' not in x]
if sobran:
    sys.exit('el tramo de la portada tiene reglas ajenas: %s' % sobran)
src = src[:ini] + ('/* La portada (logo + "Cartera de propiedades") se quito: el sitio ya\n'
                   '   tiene su propio encabezado y se veia repetido. */\n\n') + src[fin:]

# ══════════════════════════════════════════════════════════════════════
# 4. VERIFICACION
# ══════════════════════════════════════════════════════════════════════
problemas = []
for i, js in enumerate(re.findall(r'<script>(.*?)</script>', src, re.S)):
    f = os.path.join(tempfile.gettempdir(), 'chk_cat_%d.js' % i)
    open(f, 'w', encoding='utf-8').write(js)
    r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
    if r.returncode:
        problemas.append('JS invalido en el bloque %d: %s' % (i, r.stderr.split(chr(10))[2].strip()[:90]))
if src.count('<style>') != src.count('</style>'): problemas.append('<style> desparejado')
if src.count('<script') != src.count('</script>'): problemas.append('<script> desparejado')
# Sin comentarios: los propios comentarios del bloque mencionan <body> al
# explicar donde viven los modales, y eso no es una etiqueta de documento.
limpio = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
limpio = re.sub(r'<!--.*?-->', '', limpio, flags=re.S)
for t in ['<!doctype', '<html', '<head', '<body']:
    if t in limpio.lower(): problemas.append('contiene ' + t)
if 'cpm-hero' in src:      problemas.append('quedan restos de la portada')
if 'cpmLogoHero' in src:   problemas.append('queda el logo de la portada')
if 'grid-template-rows' not in src: problemas.append('falta el colapso de la fila de rejilla')
if 'CABECERA-r.top' not in src.replace(' ', ''): problemas.append('la banda no descuenta la cabecera')

print('  portada eliminada          :', 'cpm-hero' not in src)
print('  colapso con !important     :', src.count("setProperty('height','auto','important')"))
print('  problemas                  :', problemas or 'ninguno')
if problemas:
    sys.exit(1)
open(DESTINO, 'w', encoding='utf-8').write(src)
print('  escrito                    :', round(len(src) / 1024), 'KB ->', DESTINO)
