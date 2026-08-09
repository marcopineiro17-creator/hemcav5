#!/usr/bin/env python3
"""Actualiza los destinos de la landing principal de CPM y arregla el chip de
cifras en movil. Parte siempre del archivo original: reproducible."""
import re, sys, subprocess, tempfile, os

FUENTE  = '/home/user/hemcav5/src/cpm-home-original.html'
DESTINO = '/home/user/hemcav5/inicio-embed-hostinger.html'

src = open(FUENTE, encoding='utf-8').read()

# ═══════════════════ 1. DESTINOS ═══════════════════
# Cada enlace declara CON QUE PALABRA buscarse en el menu real del sitio y a
# que ruta caer si no aparece. Es la unica tabla que hay que tocar si alguna
# direccion cambia.
#
# Las claves de HEMCA y HMS son deliberadamente estrechas: si se incluyera
# "construccion" o "marketing", el menu del sitio podria devolver esas otras
# paginas y el enlace acabaria donde no se pidio.
#
#   texto del enlace/tarjeta -> (claves en el menu, ruta de respaldo, seccion)
DESTINOS = [
    # --- las seis tarjetas del ecosistema ---
    ('Venta y promoción inmobiliaria',        'servicios inmobiliarios|inmobiliaria', '/servicios-inmobiliarios', 'venta|promocion'),
    ('Servicios legales',                     'legal|division legal|juridico',        '/division-legal',          ''),
    ('Marketing inmobiliario y empresarial',  'hms|hummingbird',                      '/hms',                     ''),
    ('Construcción y remodelación',           'hemca',                                '/hemca',                   ''),
    ('Desarrollo, ejecución y venta',         'servicios inmobiliarios|inmobiliaria', '/servicios-inmobiliarios', 'desarrollo'),
    ('Avalúo y escrituración',                'regularizacion|regularizacion de predios', '/regularizacion-predios', ''),
]
# Los demas enlaces del bloque conservan su ruta actual como respaldo: si el
# menu los tiene, se usa la del sitio; si no, todo queda como estaba.
OTROS = {
    '/divisiones':              ('divisiones', '/divisiones'),
    '/catalogo-de-propiedades': ('propiedades|catalogo de propiedades|inmuebles', '/catalogo-de-propiedades'),
    '/contacto':                ('contacto|contactanos', '/contacto'),
}

# Cada tarjeta se trata por separado: un patron que abarque de un <a> al
# siguiente acabaria escribiendo el destino de una tarjeta en la anterior.
TARJETA = re.compile(r'<a class="card glass rv d\d".*?</a>', re.S)

def marca_tarjeta(titulo, claves, ruta, seccion):
    """Reescribe el <a> de la tarjeta cuyo <h3> es `titulo`."""
    global src
    extra = ' data-cpm="%s" data-cpm-ruta="%s"' % (claves, ruta)
    if seccion:
        extra += ' data-cpm-seccion="%s"' % seccion
    encontradas = [0]

    def cambia(m):
        bloque = m.group(0)
        if ('<h3>' + titulo + '</h3>') not in bloque:
            return bloque
        encontradas[0] += 1
        return re.sub(r'href="[^"]*"', 'href="' + ruta + '"' + extra, bloque, count=1)

    src = TARJETA.sub(cambia, src)
    if encontradas[0] != 1:
        sys.exit('tarjeta no encontrada o ambigua (%d): %s' % (encontradas[0], titulo))

for titulo, claves, ruta, seccion in DESTINOS:
    marca_tarjeta(titulo, claves, ruta, seccion)

for ruta, (claves, respaldo) in OTROS.items():
    src, n = re.subn(r'href="' + re.escape(ruta) + r'"',
                     'href="%s" data-cpm="%s" data-cpm-ruta="%s"' % (ruta, claves, respaldo), src)
    if not n:
        sys.exit('no se encontro ningun enlace a ' + ruta)

# Ya no debe quedar ninguna ruta relativa sin declarar.
sueltos = [h for h in re.findall(r'href="(/[^"#]*)"(?![^>]*data-cpm)', src)]
if sueltos:
    sys.exit('enlaces sin destino declarado: %s' % sueltos)

# ═══════════════════ 2. CHIP DE CIFRAS EN MOVIL ═══════════════════
# Con flex-wrap el tercer dato ("10+ Años") se caia a una segunda linea y el
# chip crecia hacia arriba tapando la foto. Pasa a ser una rejilla de tres
# columnas con sus dos separadores: los tres datos caben siempre en una linea.
VIEJO_MOVIL = """@media(max-width:620px){
  #cpm-home .cards{grid-template-columns:1fr}
  #cpm-home .hero-btns .btn{width:100%}
  #cpm-home .mosaico{gap:8px}
  #cpm-home .chip-foto{flex-wrap:wrap;gap:10px}
}"""
NUEVO_MOVIL = """@media(max-width:620px){
  #cpm-home .cards{grid-template-columns:1fr}
  #cpm-home .hero-btns .btn{width:100%}
  #cpm-home .mosaico{gap:8px}
  /* Los tres datos en una sola linea, cada uno en su columna y los
     separadores en las suyas. Con flex-wrap el tercero ("10+ Años") se caia
     abajo y, como el chip esta anclado por su borde inferior, crecia hacia
     arriba y se comia la foto. Una rejilla no puede envolver. */
  #cpm-home .chip-foto{
    display:grid;grid-template-columns:1fr 1px 1fr 1px 1fr;
    align-items:center;gap:0 9px;
    left:10px;right:10px;bottom:10px;padding:11px 12px;border-radius:14px;
  }
  #cpm-home .chip-foto>div{min-width:0;text-align:center}
  #cpm-home .chip-foto i{align-self:center;height:28px}
  #cpm-home .chip-foto b{font-size:clamp(1rem,4.6vw,1.3rem)}
  #cpm-home .chip-foto span{
    font-size:9px;letter-spacing:.05em;line-height:1.25;
    display:block;margin-top:5px;overflow-wrap:anywhere;
  }
}
@media(max-width:380px){
  #cpm-home .chip-foto{gap:0 6px;padding:9px 8px}
  #cpm-home .chip-foto span{font-size:8px;letter-spacing:.02em}
}"""
if VIEJO_MOVIL not in src:
    sys.exit('no se encontro el bloque responsive de 620px')
src = src.replace(VIEJO_MOVIL, NUEVO_MOVIL, 1)

# ═══════════════════ 3. RESOLUCION DE ENLACES ═══════════════════
VIEJO_JS = """/* Abrir enlaces fuera del iframe de Hostinger. */
q('a[href]').forEach(function(a){
  var h=a.getAttribute('href')||'';
  if(/^(#|mailto:|tel:|javascript:)/i.test(h)) return;   /* anclas y contactos se quedan igual */
  a.setAttribute('target',DESTINO);
  if(DESTINO==='_blank') a.setAttribute('rel','noopener');
});"""

NUEVO_JS = r"""/* Abrir enlaces fuera del iframe de Hostinger. */
q('a[href]').forEach(function(a){
  var h=a.getAttribute('href')||'';
  if(/^(#|mailto:|tel:|javascript:)/i.test(h)) return;   /* anclas y contactos se quedan igual */
  a.setAttribute('target',DESTINO);
  if(DESTINO==='_blank') a.setAttribute('rel','noopener');
});

/* ═══════════ A DONDE VA CADA TARJETA ═══════════
   Las rutas escritas a mano se quedan viejas en cuanto el sitio cambia una
   pagina de sitio, que es justo lo que estaba pasando. Asi que en vez de
   confiar en ellas, cada enlace dice CON QUE PALABRA buscarse (data-cpm) y a
   donde caer si no aparece (data-cpm-ruta): se lee el menu REAL del sitio y
   se enlaza justo donde enlaza la propia navegacion. Si el destino no esta
   en el menu, se usa la ruta de respaldo y todo sigue igual que antes.

   Ademas la ruta se vuelve absoluta: dentro del iframe una ruta relativa se
   resuelve contra la direccion del marco, no contra la del sitio. */
var ORIGEN='https://www.cpmempresarial.com';
(function(){
  var o='';
  try{ o=(window.parent&&window.parent.location&&window.parent.location.origin)||''; }catch(e){ o=''; }
  if(!/^https?:/.test(o)){ try{ o=location.origin||''; }catch(e){ o=''; } }
  if(/^https?:/.test(o)) ORIGEN=o;
})();

function sinTildes(t){
  t=(t||'').toLowerCase();
  try{ t=t.normalize('NFD').replace(/[\u0300-\u036f]/g,''); }catch(e){}
  return t.replace(/\s+/g,' ').trim();
}

/* Rutas del menu del sitio, indexadas por el texto que las nombra. */
var menuSitio=null;
function leerMenu(){
  if(menuSitio) return menuSitio;
  menuSitio={};
  try{
    var doc=(MARCO.win&&MARCO.win.document)||document;
    var anclas=doc.querySelectorAll('a[href]');
    for(var i=0;i<anclas.length;i++){
      var a=anclas[i], h=a.getAttribute('href')||'';
      if(/^(#|mailto:|tel:|javascript:)/i.test(h)) continue;
      if(root.contains(a)) continue;            /* los de este bloque no cuentan */
      var u; try{ u=new URL(h,doc.baseURI); }catch(e){ continue; }
      if(u.origin!==ORIGEN) continue;
      if(!u.pathname.replace(/\/+$/,'')) continue;          /* la portada */
      var t=sinTildes(a.textContent);
      if(!t||t.length>40) continue;
      /* Paginas de tramite: sus nombres se parecen demasiado a los de las
         divisiones ("aviso legal" no es la division legal). */
      if(/aviso|privacidad|terminos|cookies|politica|blog/.test(t)) continue;
      if(!menuSitio[t]) menuSitio[t]=u.href;
    }
  }catch(e){}
  return menuSitio;
}

/* Coincidencia exacta o por el principio del texto. Nada de buscar la
   palabra en cualquier posicion: asi es como se acaba enlazando la division
   legal al aviso legal. */
function rutaDelSitio(claves){
  var m=leerMenu(), i, t;
  for(i=0;i<claves.length;i++){ if(m[sinTildes(claves[i])]) return m[sinTildes(claves[i])]; }
  for(i=0;i<claves.length;i++){
    var k=sinTildes(claves[i]);
    for(t in m){ if(Object.prototype.hasOwnProperty.call(m,t) && t.indexOf(k)===0) return m[t]; }
  }
  return null;
}

q('a[data-cpm]').forEach(function(a){
  var claves=(a.getAttribute('data-cpm')||'').split('|');
  var respaldo=a.getAttribute('data-cpm-ruta')||'/';
  a.setAttribute('href', rutaDelSitio(claves) || (ORIGEN+respaldo));
});

/* ═══════════ Y A QUE SECCION DE ESA PAGINA ═══════════
   Dos tarjetas apuntan a la misma pagina pero a apartados distintos. Los
   identificadores de esa pagina no se pueden saber desde aqui, asi que se
   miran cuando hacen falta: al pasar por encima de la tarjeta (o tocarla) se
   pide la pagina UNA vez, se busca el titulo que corresponde y se le anade su
   ancla al enlace. Si algo falla -- no hay red, la pagina cambio, no existe
   ese apartado -- el enlace se queda apuntando a la pagina, que es
   exactamente el comportamiento de antes. Un ancla que no existe tampoco
   rompe nada: el navegador abre la pagina por arriba. */
var secciones=null;
function buscarSecciones(url){
  if(secciones) return secciones;
  secciones=new Promise(function(res){
    try{
      fetch(url,{credentials:'same-origin'})
        .then(function(r){ return r.ok?r.text():''; })
        .then(function(html){
          var out=[];
          try{
            var doc=new DOMParser().parseFromString(html,'text/html');
            var tit=doc.querySelectorAll('h1,h2,h3');
            for(var i=0;i<tit.length;i++){
              var t=sinTildes(tit[i].textContent);
              var n=tit[i];
              while(n && !n.id) n=n.parentElement;
              if(n && n.id && t) out.push({id:n.id,t:t});
            }
          }catch(e){}
          res(out);
        })
        .catch(function(){ res([]); });
    }catch(e){ res([]); }
  });
  return secciones;
}
q('a[data-cpm-seccion]').forEach(function(a){
  var pedido=false;
  function resolver(){
    if(pedido) return; pedido=true;
    var base=a.getAttribute('href')||'';
    if(!/^https?:/.test(base)) return;
    var claves=(a.getAttribute('data-cpm-seccion')||'').split('|').map(sinTildes);
    buscarSecciones(base).then(function(lista){
      for(var i=0;i<lista.length;i++){
        var todas=true;
        for(var j=0;j<claves.length;j++){ if(lista[i].t.indexOf(claves[j])===-1){ todas=false; break; } }
        if(todas){ a.setAttribute('href', base.split('#')[0]+'#'+lista[i].id); return; }
      }
    });
  }
  ['pointerenter','touchstart','focus'].forEach(function(ev){
    a.addEventListener(ev,resolver,{passive:true,once:true});
  });
});"""

if VIEJO_JS not in src:
    sys.exit('no se encontro el bloque que fija el target de los enlaces')
src = src.replace(VIEJO_JS, NUEVO_JS, 1)

# ═══════════════════ 4. VERIFICACION ═══════════════════
problemas = []
for i, js in enumerate(re.findall(r'<script>(.*?)</script>', src, re.S)):
    f = os.path.join(tempfile.gettempdir(), 'chk_home_%d.js' % i)
    open(f, 'w', encoding='utf-8').write(js)
    r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
    if r.returncode:
        problemas.append('JS invalido en el bloque %d: %s' % (i, r.stderr.split(chr(10))[2].strip()[:80]))
if src.count('<style>') != src.count('</style>'): problemas.append('<style> desparejado')
if src.count('<script') != src.count('</script>'): problemas.append('<script> desparejado')
for t in ['<!doctype', '<html', '<head', '<body']:
    if t in src.lower(): problemas.append('contiene ' + t)
if src.count('flex-wrap:wrap') and 'chip-foto{flex-wrap' in src.replace(' ', ''):
    problemas.append('el chip sigue envolviendo en movil')

print('  destinos declarados        :', len(re.findall(r'data-cpm="', src)))
print('  tarjetas con seccion       :', len(re.findall(r'data-cpm-seccion="', src)))
print('  problemas                  :', problemas or 'ninguno')
if problemas:
    sys.exit(1)
open(DESTINO, 'w', encoding='utf-8').write(src)
print('  escrito                    :', round(len(src) / 1024), 'KB ->', DESTINO)
