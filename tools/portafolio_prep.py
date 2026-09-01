#!/usr/bin/env python3
"""Repara y amplia el PORTAFOLIO DE ASESORES de CPM. Parte siempre del
original pegado en src/, nunca de la salida anterior.

Cuatro asuntos, en este orden:
  1. Coordenadas: campo propio en el editor de la propiedad, al lado del
     enlace de Maps. Se guardan en el documento del inmueble y viajan al
     catalogo publico, que es de donde las lee la pagina del mapa.
  2. Exclusivas: se ven en la vista del asesor con su leyenda, se puede
     descargar su ficha, y nunca se publican.
  3. Revision: un panel de solo-admin que dice, propiedad por propiedad,
     que hay guardado y por que sale o no sale. Es la unica forma de
     contestar "que paso con esas propiedades" sin adivinar.
  4. Robustez: un documento con un campo mal puesto tumbaba la lista
     entera; ahora se salta y se avisa.
"""
import os
import re
import subprocess
import sys
import tempfile

RAIZ = '/home/user/hemcav5'
FUENTE = os.path.join(RAIZ, 'src/cpm-portafolio-original.html')
DESTINO = os.path.join(RAIZ, 'portafolio-asesores-embed-hostinger.html')
MAPA_JS = os.path.join(RAIZ, 'tools/mapa_js.txt')

src = open(FUENTE, encoding='utf-8').read()


def cambia(viejo, nuevo, que, veces=1):
    global src
    n = src.count(viejo)
    if n != veces:
        sys.exit('no se encontro (%d de %d): %s' % (n, veces, que))
    src = src.replace(viejo, nuevo, veces)


def sin_comentarios(t):
    """Quita comentarios CSS, HTML y de linea de JS. Las revisiones de
    'esto ya no debe estar' se hacen sobre esto: los comentarios explican
    justamente lo que se quito y se delatarian a si mismos."""
    t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
    t = re.sub(r'<!--.*?-->', '', t, flags=re.S)
    return t


def tabla(nombre):
    """Saca una tabla de coordenadas del guion del mapa, tal cual.

    Copiarla a mano seria pedir que las dos paginas se desajusten con el
    tiempo: si manana se agrega un pueblo al mapa, aqui llegaria solo.
    """
    txt = open(MAPA_JS, encoding='utf-8').read()
    m = re.search(r'( *var ' + nombre + r' = \{.*?\n *\};)', txt, re.S)
    if not m:
        sys.exit('no se encontro la tabla ' + nombre + ' en tools/mapa_js.txt')
    return m.group(1).strip()


# ══════════════════════════════════════════════════════════════════════
# 1. QUIEN ES ADMIN
#    La comparacion era sensible a mayusculas contra una lista en
#    minusculas. Firebase devuelve el correo tal como se dio de alta, asi
#    que una cuenta creada como "Marco@..." se quedaba sin ser admin: sin
#    boton de Nueva, sin Sincronizar y -- antes de este cambio -- sin ver
#    las exclusivas. Es justo el sintoma reportado.
# ══════════════════════════════════════════════════════════════════════
cambia(
    """  function isAdmin(){ return user && ADMINS.indexOf(user.email)>=0; }""",
    """  function correoNorm(c){ return String(c==null?'':c).trim().toLowerCase(); }
  function isAdmin(){ return !!user && ADMINS.indexOf(correoNorm(user.email))>=0; }
  /* ─────────────────────────────────────────────────────────
     CATEGORIAS Y EXCLUSIVAS
     El campo `categorias` viene de Firestore y no siempre es un arreglo:
     puede llegar como texto suelto si se capturo desde la consola. Sin
     esta lectura tolerante, un solo documento asi tumbaba la lista
     entera (ver el listener de Firestore mas abajo).

     Y una propiedad se toma por exclusiva si CUALQUIERA de sus
     categorias contiene "exclusiv", no solo si dice exactamente
     "Exclusivos (no publicar)". Las etiquetadas antes de que existiera
     esa opcion -- "Exclusiva", "EXCLUSIVOS", "exclusivo" -- contaban
     como normales y se habrian publicado.
     ───────────────────────────────────────────────────────── */
  function cats(t){
    var c = t && t.categorias;
    if(!c) return [];
    if(typeof c === 'string') return c.split(/[,;|]/).map(function(x){ return x.trim(); }).filter(Boolean);
    if(Object.prototype.toString.call(c) === '[object Array]') return c.filter(function(x){ return typeof x === 'string'; });
    if(typeof c === 'object') return Object.keys(c).filter(function(k){ return c[k]; });
    return [];
  }
  function esExclusiva(t){
    var c = cats(t);
    for(var i=0;i<c.length;i++){ if(norm(c[i]).indexOf('exclusiv')>=0) return true; }
    return false;
  }""", 'isAdmin')

# El indice de busqueda usaba .join() sobre el campo crudo.
cambia("""    var texto=norm([t.id,t.nombre,t.tipo,t.ciudad,t.estado,t.descripcion,(t.categorias||[]).join(' ')].join(' '));""",
       """    var texto=norm([t.id,t.nombre,t.tipo,t.ciudad,t.estado,t.descripcion,cats(t).join(' ')].join(' '));""",
       'indexar')

# ══════════════════════════════════════════════════════════════════════
# 2. CAMPOS QUE VIAJAN AL CATALOGO PUBLICO
#    Sin lat/lng aqui, las coordenadas que se capturen en el editor no
#    llegarian nunca a catalogo_publico, que es la coleccion que lee la
#    pagina del mapa. El campo se anade al espejo, no a la ficha publica:
#    son datos de ubicacion, ya publicos por el enlace de Maps.
# ══════════════════════════════════════════════════════════════════════
cambia("""  var CAMPOS_PUBLICOS = ["id","nombre","tipo","ciudad","estado","descripcion",
    "precio","precio_total","dimensiones_m2","hectareas","precio_m2",
    "ubicacion_maps","fotos","estado_propiedad"];""",
       """  var CAMPOS_PUBLICOS = ["id","nombre","tipo","ciudad","estado","descripcion",
    "precio","precio_total","dimensiones_m2","hectareas","precio_m2",
    "ubicacion_maps","fotos","estado_propiedad","lat","lng"];""",
       'CAMPOS_PUBLICOS')

# ══════════════════════════════════════════════════════════════════════
# 3. MODULO DE COORDENADAS
#    Mismo calculo que la pagina del mapa, y las mismas tablas, sacadas
#    de su guion para que no se desajusten. Todo es aritmetica: ni red ni
#    API ni clave de Google.
# ══════════════════════════════════════════════════════════════════════
MODULO = """  /* ═══════════════════════════════════════════════════
     COORDENADAS
     Lo que se puede pegar en el campo del editor:
       · un par de numeros   21.067187, -89.504562
       · un Plus Code        3F8W+V5      (lo que se copia del movil)
       · un enlace LARGO de Maps, del que se sacan los numeros
     Los enlaces cortos (maps.app.goo.gl) no llevan coordenadas dentro:
     no hay nada que sacar de ellos sin abrirlos.

     El Plus Code corto le faltan cuatro caracteres, que se recuperan de
     la localidad de la propiedad: por eso hace falta que la ciudad este
     escrita. Un codigo completo (11 caracteres) no necesita referencia.
     ═══════════════════════════════════════════════════ */
  function valida(lat, lng){
    lat = Number(lat); lng = Number(lng);
    if(!isFinite(lat) || !isFinite(lng)) return null;
    if(lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
    if(lat === 0 && lng === 0) return null;        /* el 0,0 es dato vacio */
    return [lat, lng];
  }
  var OLC_A = "23456789CFGHJMPQRVWX";
  function olcLimpio(c){ return String(c==null?'':c).toUpperCase().replace(/[^0-9A-Z+]/g,''); }
  function olcCodifica(lat, lng){
    lat = Math.min(89.999999, Math.max(-90, lat));
    lng = ((lng + 180) % 360 + 360) % 360 - 180;
    var latV = lat + 90, lngV = lng + 180, res = 20, code = '';
    for(var i=0;i<5;i++){
      var la = Math.floor(latV/res), ln = Math.floor(lngV/res);
      if(la > 19) la = 19;
      if(ln > 19) ln = 19;
      code += OLC_A.charAt(la) + OLC_A.charAt(ln);
      latV -= la*res; lngV -= ln*res;
      res /= 20;
    }
    return code.substr(0,8) + '+' + code.substr(8);
  }
  function olcDecodifica(code){
    var c = olcLimpio(code).replace(/\\+/g,'').replace(/0+$/,'');
    if(c.length < 2) return null;
    var latBaja = -90, lngBaja = -180, res = 20, alto = 20, ancho = 20;
    for(var k=0;k+1<c.length && k<10;k+=2){
      var ia = OLC_A.indexOf(c.charAt(k)), ib = OLC_A.indexOf(c.charAt(k+1));
      if(ia < 0 || ib < 0) return null;
      latBaja += ia*res; lngBaja += ib*res;
      alto = ancho = res; res /= 20;
    }
    /* A partir del caracter 11 el codigo deja de ir por pares y afina con
       una rejilla de 5 filas por 4 columnas. Sin esto, un codigo de 11
       caracteres se leia como uno de 10: celda de 13,9 m en vez de 2,8. */
    for(var j=10;j<c.length && j<15;j++){
      var ig = OLC_A.indexOf(c.charAt(j));
      if(ig < 0) break;
      alto /= 5; ancho /= 4;
      latBaja += Math.floor(ig/4)*alto;
      lngBaja += (ig%4)*ancho;
    }
    return {lat:latBaja + alto/2, lng:lngBaja + ancho/2, celda:Math.max(alto,ancho)};
  }
  function olcRecupera(corto, refLat, refLng){
    var c = olcLimpio(corto), sep = c.indexOf('+');
    if(sep < 0){
      if(/^[23456789CFGHJMPQRVWX]{8,11}$/.test(c)){ c = c.substr(0,8)+'+'+c.substr(8); sep = 8; }
      else return null;
    }
    if(sep === 8) return olcDecodifica(c);
    var faltan = 8 - sep;
    if(faltan <= 0 || faltan % 2) return null;
    if(refLat == null || refLng == null) return null;
    var prefijo = olcCodifica(refLat, refLng).replace('+','').substr(0, faltan);
    var pleno = prefijo + c.replace('+','');
    pleno = pleno.substr(0,8) + '+' + pleno.substr(8);
    var a = olcDecodifica(pleno);
    if(!a) return null;
    /* Al area mas cercana a la referencia: sin esto, un codigo junto a un
       limite de rejilla se resuelve una celda entera desplazado. */
    var resol = Math.pow(20, 2 - (faltan/2)), mitad = resol/2;
    if(refLat + mitad < a.lat && a.lat - resol >= -90) a.lat -= resol;
    else if(refLat - mitad > a.lat && a.lat + resol <= 90) a.lat += resol;
    if(refLng + mitad < a.lng && a.lng - resol >= -180) a.lng -= resol;
    else if(refLng - mitad > a.lng && a.lng + resol <= 180) a.lng += resol;
    return a;
  }
  var RE_PLUS = /\\b([23456789CFGHJMPQRVWX]{2,8}\\+[23456789CFGHJMPQRVWX]{2,3})\\b/i;
  function plusEnTexto(txt, refLat, refLng){
    var m = String(txt||'').match(RE_PLUS);
    if(!m) return null;
    var a = olcRecupera(m[1], refLat, refLng);
    return a ? valida(a.lat, a.lng) : null;
  }
  function coordsDeUrl(url){
    var u = String(url||'');
    if(!/^https?:/i.test(u)) return null;
    var pats = [
      /!3d(-?\\d{1,3}\\.\\d+)!4d(-?\\d{1,3}\\.\\d+)/,
      /@(-?\\d{1,3}\\.\\d+),(-?\\d{1,3}\\.\\d+)/,
      /[?&](?:q|query|ll|center|daddr|sll)=(-?\\d{1,3}\\.\\d+)%2C(-?\\d{1,3}\\.\\d+)/i,
      /[?&](?:q|query|ll|center|daddr|sll)=(-?\\d{1,3}\\.\\d+),\\s*(-?\\d{1,3}\\.\\d+)/i,
      /\\/(-?\\d{1,3}\\.\\d+),(-?\\d{1,3}\\.\\d+)(?:[/?#]|$)/
    ];
    for(var i=0;i<pats.length;i++){
      var m = u.match(pats[i]);
      if(m){ var v = valida(m[1], m[2]); if(v) return v; }
    }
    return null;
  }
__LOCALIDADES__
__CENTRO__
  function coordsDeLocalidad(ciudad, estado){
    var c = norm(ciudad);
    if(c && LOCALIDADES[c]) return LOCALIDADES[c];
    if(c){
      var partes = c.split(' ');
      for(var n=partes.length;n>=1;n--){
        for(var i=0;i+n<=partes.length;i++){
          var frag = partes.slice(i,i+n).join(' ');
          if(frag.length >= 4 && LOCALIDADES[frag]) return LOCALIDADES[frag];
        }
      }
    }
    var e = norm(estado);
    if(e && CENTRO_ESTADO[e]) return CENTRO_ESTADO[e];
    return null;
  }
  /* Coordenadas ya guardadas en el inmueble. */
  function coordsDe(t){ return t ? valida(t.lat, t.lng) : null; }
  /* Lo que se pego en el campo. Devuelve {lat,lng,fuente} o null. */
  function interpretaCoords(raw, ciudad, estado){
    var s = String(raw||'').trim();
    if(!s) return null;
    if(/^https?:/i.test(s)){
      var u = coordsDeUrl(s);
      if(u) return {lat:u[0], lng:u[1], fuente:'enlace de Maps'};
    }
    var m = s.match(/(-?\\d{1,3}(?:\\.\\d+)?)\\s*[,;\\s]\\s*(-?\\d{1,3}(?:\\.\\d+)?)/);
    if(m){
      var v = valida(m[1], m[2]);
      if(v) return {lat:v[0], lng:v[1], fuente:'coordenadas'};
    }
    var ref = coordsDeLocalidad(ciudad, estado);
    var p = plusEnTexto(s, ref?ref[0]:null, ref?ref[1]:null);
    if(p) return {lat:p[0], lng:p[1], fuente:'Plus Code'};
    /* Un Plus Code corto sin ciudad reconocida no se puede completar: se
       dice asi, en vez de dejar un "no se entendio" que no orienta. */
    if(!ref && RE_PLUS.test(s)) return {error:'Ese Plus Code es corto y la ciudad "'+(ciudad||'')+'" no esta en la lista. Escribe la ciudad, o pega el codigo completo (11 caracteres).'};
    return null;
  }
  function txtCoords(lat, lng){ return Number(lat).toFixed(6)+', '+Number(lng).toFixed(6); }

"""
MODULO = MODULO.replace('__LOCALIDADES__', '  ' + tabla('LOCALIDADES'))
MODULO = MODULO.replace('__CENTRO__', '  ' + tabla('CENTRO_ESTADO'))

cambia("""  /* ═══════════════════════════════════════════════════
     BANDA VISIBLE""", MODULO + """  /* ═══════════════════════════════════════════════════
     BANDA VISIBLE""", 'sitio del modulo de coordenadas')

# ══════════════════════════════════════════════════════════════════════
# 4. UN DOCUMENTO MALO YA NO TUMBA LA LISTA
#    snap.docs.map() corria sin red: si un solo documento hacia saltar
#    una excepcion (por ejemplo, categorias guardado como texto), la
#    excepcion salia del callback de onSnapshot, `terrenos` se quedaba
#    como estaba y la rejilla no se volvia a pintar. Un dato mal puesto
#    en una propiedad escondia TODAS.
# ══════════════════════════════════════════════════════════════════════
cambia("""        unsubWatch = firebase.firestore().collection(COL_PRIVADA).onSnapshot(function(snap){
          terrenos = snap.docs.map(function(d){
            var o=d.data()||{};
            if(!o.id) o.id=d.id;
            return indexar(o);
          }).sort(function(a,b){ return String(a.id).localeCompare(String(b.id)); });""",
       """        unsubWatch = firebase.firestore().collection(COL_PRIVADA).onSnapshot(function(snap){
          docsMalos=[];
          terrenos = snap.docs.map(function(d){
            try{
              var o=d.data()||{};
              if(!o.id) o.id=d.id;
              return indexar(o);
            }catch(e){
              docsMalos.push(d.id+' ('+(e&&e.message||'ilegible')+')');
              return null;
            }
          }).filter(Boolean).sort(function(a,b){ return String(a.id).localeCompare(String(b.id)); });
          if(docsMalos.length) console.warn('[CPM] documentos ilegibles:', docsMalos);""",
       'listener de Firestore')

cambia("""  var user = null, terrenos = [], filtro = "Todos", q = "";""",
       """  var user = null, terrenos = [], filtro = "Todos", q = "";
  /* Documentos que no se pudieron leer en la ultima lectura. Se muestran
     en el panel de revision para que no se pierdan en silencio. */
  var docsMalos = [];""", 'estado')

# ══════════════════════════════════════════════════════════════════════
# 5. LAS EXCLUSIVAS SE VEN EN LA VISTA DEL ASESOR
#    Antes solo las veia un admin. Ahora las ve cualquier asesor con
#    sesion, con su leyenda y con su ficha descargable; lo que no cambia
#    es que no se publican.
# ══════════════════════════════════════════════════════════════════════
cambia("""  function visibles(){
    var base = terrenos.slice();
    if(!isAdmin()) base = base.filter(function(t){ return !(t.categorias && t.categorias.indexOf('Exclusivos (no publicar)')>=0); });
    return base;
  }""",
       """  /* Todo lo que hay, para todos los que entran. La cartera es privada
     de por si: para llegar aqui hace falta una cuenta de CPM. */
  function visibles(){ return terrenos.slice(); }""", 'visibles')

cambia("""    if(cat==='Exclusivos') return terrenos.filter(function(t){return t.categorias && t.categorias.indexOf('Exclusivos (no publicar)')>=0}).length;
    return base.filter(function(t){return t.categorias && t.categorias.indexOf(cat)>=0}).length;""",
       """    if(cat==='Exclusivos') return base.filter(esExclusiva).length;
    return base.filter(function(t){return cats(t).indexOf(cat)>=0}).length;""", 'count')

cambia("""      if(filtro==='Exclusivos'){ return isAdmin() && t.categorias && t.categorias.indexOf('Exclusivos (no publicar)')>=0; }
      if(!isAdmin() && t.categorias && t.categorias.indexOf('Exclusivos (no publicar)')>=0) return false;
      if(filtro==='Terrenos' && t.tipo!=='Terreno Particular') return false;
      if(filtro==='Macrolotes' && t.tipo!=='Macrolote') return false;
      if(['Playa','Casas','Departamentos','Ranchos y Haciendas'].indexOf(filtro)>=0){
        if(!t.categorias || t.categorias.indexOf(filtro)<0) return false;
      }""",
       """      if(filtro==='Exclusivos') return esExclusiva(t);
      if(filtro==='Terrenos' && t.tipo!=='Terreno Particular') return false;
      if(filtro==='Macrolotes' && t.tipo!=='Macrolote') return false;
      if(['Playa','Casas','Departamentos','Ranchos y Haciendas'].indexOf(filtro)>=0){
        if(cats(t).indexOf(filtro)<0) return false;
      }""", 'porCategoria')

cambia("""    var pills = CATS.filter(function(c){ return c!=='Exclusivos' || admin; }).map(function(c){""",
       """    /* El filtro de exclusivas ya no es solo del admin: ahora las ve
       cualquier asesor, asi que tambien puede filtrarlas. */
    var pills = CATS.map(function(c){""", 'pills')

# ══════════════════════════════════════════════════════════════════════
# 6. LA LEYENDA
#    En la tarjeta, un sello discreto arriba a la derecha; en la ficha,
#    una linea que dice lo unico que hay que saber: que no se publica.
# ══════════════════════════════════════════════════════════════════════
cambia("""#cpm-portafolio .cpm-card .capas{""",
       """/* Sello de propiedad exclusiva. Va donde el banderin de la destacada,
   pero nunca coinciden: la destacada no es exclusiva. */
#cpm-portafolio .cpm-card .excl{
  position:absolute;top:10px;right:10px;z-index:3;
  background:rgba(122,26,26,.92);color:#ffe9e9;
  font-size:8px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;
  padding:4px 9px;border-radius:20px;
  box-shadow:0 2px 8px rgba(0,0,0,.3);
}
#cpm-portafolio .cpm-card .capas{""", 'CSS del sello')

cambia("""      var flag  = (t._premium&&t._flag) ? '<div class="flag">'+esc(t._flag)+'</div>' : '';""",
       """      var flag  = (t._premium&&t._flag) ? '<div class="flag">'+esc(t._flag)+'</div>' : '';
      var sello = esExclusiva(t) ? '<div class="excl">Exclusiva</div>' : '';""", 'sello en la tarjeta')

cambia("""          '<div class="tipo">'+esc(t._etiqueta||tipoCorto(t.tipo))+'</div>'+ flag +""",
       """          '<div class="tipo">'+esc(t._etiqueta||tipoCorto(t.tipo))+'</div>'+ flag + sello +""",
       'sello en la maquetacion de la tarjeta')

cambia("""    var cats=(t.categorias&&t.categorias.length)?'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px">'+t.categorias.map(""",
       """    var leyenda = esExclusiva(t)
      ? '<div style="display:flex;align-items:center;gap:8px;background:#fdf0f0;border:1px solid #eccaca;border-radius:10px;padding:9px 12px;margin-bottom:10px">'+
        '<span style="font-size:14px">\\ud83d\\udd12</span>'+
        '<span style="font-size:11px;line-height:1.5;color:#8a3b3b"><b>Propiedad exclusiva.</b> No se publica en el cat\\u00e1logo p\\u00fablico. '+
        'Puedes descargar su ficha y compartirla directo con tu cliente.</span></div>'
      : '';
    var listaCats=cats(t);
    var catsHTML=(listaCats.length)?'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px">'+listaCats.map(""",
       'leyenda de la ficha')

cambia("""          cats+
          '<h2 style=""",
       """          catsHTML+ leyenda +
          '<h2 style=""", 'sitio de la leyenda en la ficha')

# La ficha usaba la variable `cats`, que ahora es el nombre de la funcion.
# Con `var cats` dentro de openFicha, la funcion quedaria tapada por la
# variable local en TODA la funcion (izado), y esExclusiva -- que se llama
# antes -- reventaria. De ahi el renombre a catsHTML.

# ══════════════════════════════════════════════════════════════════════
# 7. EL CAMPO DE COORDENADAS EN EL EDITOR
# ══════════════════════════════════════════════════════════════════════
cambia("""        txt('ID','id')+txt('Nombre','nombre')+txt('Ciudad','ciudad')+txt('Estado','estado')+txt('URL Maps','ubicacion_maps')+""",
       """        txt('ID','id')+txt('Nombre','nombre')+txt('Ciudad','ciudad')+txt('Estado','estado')+txt('URL Maps','ubicacion_maps')+
        campoCoords()+""", 'campo de coordenadas en el editor')

cambia("""    var estadoRadios = ESTADOS.map(function(e){""",
       """    /* ─────────────────────────────────────────────────────────
       COORDENADAS
       Aparte del enlace de Maps a proposito: el enlace es para que una
       persona lo abra, y las coordenadas son para que el mapa sepa donde
       poner el alfiler. Los enlaces cortos no traen coordenadas dentro,
       asi que uno no sustituye al otro.
       ───────────────────────────────────────────────────────── */
    function campoCoords(){
      var v = coordsDe(f), ini = v ? txtCoords(v[0], v[1]) : '';
      return '<div style="margin-bottom:10px">'+
        '<label style="font-size:10px;font-weight:600;color:#5a6a7a;letter-spacing:1px;text-transform:uppercase;display:block;margin-bottom:3px">Coordenadas <span style="font-weight:400;text-transform:none;letter-spacing:0;color:#a0b0c0">(para el mapa)</span></label>'+
        '<input id="cpm-ed-coords" inputmode="text" autocapitalize="characters" spellcheck="false" value="'+esc(ini)+'" placeholder="21.067187, -89.504562   \\u00f3   3F8W+V5" style="width:100%;padding:9px 12px;border:2px solid #e8ecf0;border-radius:10px;font-size:13px;outline:none">'+
        '<div id="cpm-ed-coords-st" style="font-size:11px;line-height:1.5;margin-top:5px;color:#7a8a9a"></div>'+
        '<div id="cpm-ed-coords-ac" style="margin-top:6px"></div>'+
      '</div>';
    }
    var estadoRadios = ESTADOS.map(function(e){""", 'definicion de campoCoords')

cambia("""    var fileInp=ov.querySelector('#cpm-ed-file');""",
       """    /* ── coordenadas ─────────────────────────────────────── */
    var inpC=ov.querySelector('#cpm-ed-coords');
    var stC=ov.querySelector('#cpm-ed-coords-st');
    var acC=ov.querySelector('#cpm-ed-coords-ac');
    var coordsMal=false;          /* hay texto en la caja y no se entiende */
    function guardaCoords(lat,lng){
      /* Seis decimales: 11 cm. Los mismos que se muestran, para que el
         numero guardado y el numero en pantalla sean el mismo numero. */
      f.lat=Number(Number(lat).toFixed(6));
      f.lng=Number(Number(lng).toFixed(6));
    }
    function borraCoords(){ delete f.lat; delete f.lng; }
    function pintaCoords(){
      var raw=inpC.value.trim();
      acC.innerHTML='';
      if(!raw){
        coordsMal=false; borraCoords();
        var alt=coordsDeUrl(f.ubicacion_maps);
        if(alt){
          stC.innerHTML='El enlace de Maps ya trae coordenadas: <b>'+esc(txtCoords(alt[0],alt[1]))+'</b>';
          acC.innerHTML='<button id="cpm-ed-coords-usar" style="background:#e8f2fb;color:#3d7ab5;border:none;padding:7px 12px;border-radius:9px;font-size:11px;font-weight:600">\\u2193 Usar esas</button>';
          var bu=acC.querySelector('#cpm-ed-coords-usar');
          bu.addEventListener('click',function(){ inpC.value=txtCoords(alt[0],alt[1]); pintaCoords(); });
        } else {
          var ref=coordsDeLocalidad(f.ciudad,f.estado);
          stC.innerHTML='Sin coordenadas. En el mapa saldr\\u00e1 <b>aproximada</b>, en el centro de '+
            (ref?esc(f.ciudad||f.estado):'la zona')+'. Pega aqu\\u00ed lo que copies de Google Maps.';
        }
        inpC.style.borderColor='#e8ecf0';
        return;
      }
      var r=interpretaCoords(raw,f.ciudad,f.estado);
      if(r && r.error){
        coordsMal=true; inpC.style.borderColor='#e6b0aa';
        stC.innerHTML='<span style="color:#c0392b">'+esc(r.error)+'</span>';
        return;
      }
      if(!r){
        coordsMal=true; inpC.style.borderColor='#e6b0aa';
        stC.innerHTML='<span style="color:#c0392b">No se entendi\\u00f3.</span> Pega dos n\\u00fameros separados por coma, o un Plus Code como <b>3F8W+V5</b>. '+
          'Los enlaces cortos de Maps (maps.app.goo.gl) no llevan las coordenadas dentro.';
        return;
      }
      coordsMal=false; inpC.style.borderColor='#a9dfbf';
      guardaCoords(r.lat,r.lng);
      stC.innerHTML='<span style="color:#1e8449">\\u2713 '+esc(txtCoords(r.lat,r.lng))+'</span> \\u00b7 le\\u00eddo del '+esc(r.fuente)+
        '. El alfiler del mapa queda <b>exacto</b>.';
      acC.innerHTML='<a href="https://www.google.com/maps/search/?api=1&query='+
        encodeURIComponent(r.lat+','+r.lng)+'" target="_blank" rel="noopener" style="font-size:11px;color:#3d7ab5;font-weight:600;text-decoration:none">\\u2197 Comprobar en Google Maps</a>';
    }
    inpC.addEventListener('input',pintaCoords);
    inpC.addEventListener('blur',function(){
      /* Al salir, si se entendio, se deja el texto ya normalizado. */
      if(!coordsMal){ var v=coordsDe(f); if(v) inpC.value=txtCoords(v[0],v[1]); }
    });
    pintaCoords();

    var fileInp=ov.querySelector('#cpm-ed-file');""", 'wiring de coordenadas')

cambia("""      if(!f.id){ alert('La propiedad necesita un ID.'); return; }
      ['precio','dimensiones_m2','hectareas','precio_m2','comision'].forEach(function(k){ var n=parseFloat(f[k]); f[k]=isNaN(n)?0:n; });""",
       """      if(!f.id){ alert('La propiedad necesita un ID.'); return; }
      /* No se guarda a medias: si hay algo escrito en coordenadas que no
         se entiende, se avisa en vez de dejarlo caer en silencio. */
      if(coordsMal){ alert('Revisa las coordenadas: lo que hay escrito no se entiende.\\n\\nPega dos numeros separados por coma (21.067187, -89.504562) o un Plus Code (3F8W+V5), o deja la caja vacia.'); inpC.focus(); return; }
      ['precio','dimensiones_m2','hectareas','precio_m2','comision'].forEach(function(k){ var n=parseFloat(f[k]); f[k]=isNaN(n)?0:n; });""",
       'aviso al guardar')

# ══════════════════════════════════════════════════════════════════════
# 8. SINCRONIZAR: EXCLUSIVAS FUERA, Y NO PERDER LAS COORDENADAS
#    El espejo se escribe con set(), que reemplaza el documento entero.
#    Las coordenadas que se hubieran fijado desde la pagina del mapa se
#    borrarian en la primera sincronizacion. Se adoptan antes: se copian
#    al inmueble, y desde entonces el portafolio es el que manda.
# ══════════════════════════════════════════════════════════════════════
cambia("""      if(t.categorias && t.categorias.indexOf('Exclusivos (no publicar)')>=0) return false;
      return ESTADOS_PUBLICABLES.indexOf(t.estado_propiedad||'disponible')>=0;""",
       """      if(esExclusiva(t)) return false;
      return ESTADOS_PUBLICABLES.indexOf(t.estado_propiedad||'disponible')>=0;""",
       'filtro de publicables')

cambia("""      var batch=db.batch(), quedan={};
      publicables.forEach(function(t){
        var pub={};
        CAMPOS_PUBLICOS.forEach(function(k){ if(t[k]!==undefined) pub[k]=t[k]; });
        if(t.categorias) pub.categorias=t.categorias.filter(function(c){ return c!=='Exclusivos (no publicar)'; });
        quedan[t.id]=1;
        batch.set(col.doc(String(t.id)), pub);
      });""",
       """      var batch=db.batch(), quedan={}, adoptadas=0;
      /* Coordenadas que ya estuvieran en el espejo (por ejemplo, fijadas
         desde la pagina del mapa antes de que existiera este campo). */
      var previo={};
      snap.docs.forEach(function(d){ previo[d.id]=d.data()||{}; });
      publicables.forEach(function(t){
        var pub={};
        CAMPOS_PUBLICOS.forEach(function(k){ if(t[k]!==undefined) pub[k]=t[k]; });
        if(!valida(pub.lat,pub.lng)){
          delete pub.lat; delete pub.lng;
          var ant=valida((previo[t.id]||{}).lat, (previo[t.id]||{}).lng);
          if(ant){
            pub.lat=ant[0]; pub.lng=ant[1];
            /* Y se suben al inmueble, que es la fuente desde ahora. */
            batch.set(db.collection(COL_PRIVADA).doc(String(t.id)), {lat:ant[0], lng:ant[1]}, {merge:true});
            adoptadas++;
          }
        }
        pub.categorias=cats(t).filter(function(c){ return norm(c).indexOf('exclusiv')<0; });
        quedan[t.id]=1;
        batch.set(col.doc(String(t.id)), pub);
      });
      if(adoptadas) console.log('[CPM] coordenadas adoptadas del catalogo publico:', adoptadas);""",
       'copia al espejo')

# ══════════════════════════════════════════════════════════════════════
# 9. PANEL DE REVISION (solo admin)
#    Contesta con datos, no con suposiciones: que categorias tiene cada
#    propiedad guardadas de verdad, si cuenta como exclusiva, si es
#    publicable, si esta en el catalogo publico y si tiene coordenadas.
# ══════════════════════════════════════════════════════════════════════
cambia("""        (admin?'<button class="cpm-mini" id="cpm-sync" title="Copia los campos públicos a la colección catalogo_publico">↻ Sincronizar catálogo</button>':'')+""",
       """        (admin?'<button class="cpm-mini" id="cpm-sync" title="Copia los campos públicos a la colección catalogo_publico">↻ Sincronizar catálogo</button>':'')+
        (admin?'<button class="cpm-mini" id="cpm-diag" title="Qué hay guardado en cada propiedad y por qué sale o no sale">\\ud83d\\udd0d Revisión</button>':'')+""",
       'boton de revision')

cambia("""      root.querySelector('#cpm-sync').addEventListener('click',sincronizarPublico);""",
       """      root.querySelector('#cpm-sync').addEventListener('click',sincronizarPublico);
      root.querySelector('#cpm-diag').addEventListener('click',openDiagnostico);""",
       'enlace del boton de revision')

DIAG = """  /* ═══════════════ REVISION (solo admin) ═══════════════
     Un cuadro por propiedad con lo que hay guardado de verdad. Se lee el
     catalogo publico en vivo para poder decir, de cada una, si esta
     publicada ahora mismo o no.
     ═══════════════════════════════════════════════════ */
  function openDiagnostico(){
    if(!isAdmin()) return;
    var ov=mkOverlay(2147483500);
    ov.innerHTML='<div class="cpm-sheet" style="padding:22px"><div style="font-size:13px;color:#5a6a7a">Leyendo el cat\\u00e1logo p\\u00fablico\\u2026</div></div>';
    ov.addEventListener('click',function(e){ if(e.target===ov) closeOverlay(ov); });
    firebase.firestore().collection(COL_PUBLICA).get()
      .then(function(snap){ pinta(snap, null); })
      .catch(function(e){ pinta(null, e); });

    function pinta(snap, err){
      var pub={};
      if(snap) snap.docs.forEach(function(d){ pub[d.id]=d.data()||{}; });
      var reales=terrenos.filter(function(t){ return !t._premium; });
      var nExc=0, nPubl=0, nEspejo=0, nCoord=0, informe=[];

      var filas=reales.map(function(t){
        var exc=esExclusiva(t);
        var estado=t.estado_propiedad||'disponible';
        var publicable=!exc && ESTADOS_PUBLICABLES.indexOf(estado)>=0;
        var enEspejo=!!pub[String(t.id)];
        var c=coordsDe(t);
        var cEspejo=valida((pub[String(t.id)]||{}).lat,(pub[String(t.id)]||{}).lng);
        var crudo=t.categorias;
        var crudoTxt;
        try{ crudoTxt=JSON.stringify(crudo); }catch(e2){ crudoTxt='(ilegible)'; }
        if(crudo===undefined) crudoTxt='(sin el campo)';
        if(exc) nExc++;
        if(publicable) nPubl++;
        if(enEspejo) nEspejo++;
        if(c) nCoord++;

        informe.push([String(t.id), exc?'EXCLUSIVA':'normal', estado,
                      publicable?'publicable':'no se publica',
                      enEspejo?'en catalogo':'fuera del catalogo',
                      c?txtCoords(c[0],c[1]):(cEspejo?'solo en el espejo: '+txtCoords(cEspejo[0],cEspejo[1]):'sin coordenadas'),
                      'categorias='+crudoTxt].join(' | '));

        function chip(txt,bien,neutro){
          var col=neutro?['#5a6a7a','#f0f4f8']:(bien?['#1e8449','#eafaf1']:['#c0392b','#fdf0f0']);
          return '<span style="background:'+col[1]+';color:'+col[0]+';font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;white-space:nowrap">'+esc(txt)+'</span>';
        }
        return '<div style="border:1px solid #e8ecf0;border-radius:12px;padding:11px 13px;margin-bottom:8px">'+
          '<div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline;flex-wrap:wrap">'+
            '<b style="font-size:12px;color:#1a2d42">'+esc(t.id)+'</b>'+
            '<span style="font-size:11px;color:#7a8a9a;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(t.nombre||'')+'</span>'+
          '</div>'+
          '<div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:7px">'+
            chip(exc?'\\ud83d\\udd12 exclusiva':'normal', true, !exc)+
            chip(estado, ESTADOS_PUBLICABLES.indexOf(estado)>=0, false)+
            chip(publicable?'se publica':'no se publica', publicable, exc)+
            chip(enEspejo?'en el cat\\u00e1logo':'fuera del cat\\u00e1logo', enEspejo===publicable, false)+
            chip(c?'coords exactas':(cEspejo?'coords solo en el espejo':'sin coords'), !!c, false)+
          '</div>'+
          '<div style="font-size:10.5px;color:#7a8a9a;margin-top:7px;word-break:break-word"><b>categorias</b> = <code style="background:#f4f6f9;padding:1px 5px;border-radius:5px">'+esc(crudoTxt)+'</code></div>'+
          (c?'<div style="font-size:10.5px;color:#7a8a9a;margin-top:3px"><b>lat, lng</b> = '+esc(txtCoords(c[0],c[1]))+'</div>':'')+
        '</div>';
      }).join('');

      var avisoErr = err
        ? '<div class="cpm-err" style="margin-bottom:12px">No se pudo leer el cat\\u00e1logo p\\u00fablico ('+esc(err.code||err.message||'')+'). Lo dem\\u00e1s s\\u00ed es v\\u00e1lido.</div>'
        : '';
      var avisoMalos = docsMalos.length
        ? '<div style="background:#fdf0f0;border:1px solid #eccaca;border-radius:10px;padding:10px 12px;margin-bottom:12px;font-size:11px;color:#8a3b3b"><b>'+docsMalos.length+
          ' documento(s) no se pudieron leer</b> y no salen en la lista:<br>'+esc(docsMalos.join(' \\u00b7 '))+'</div>'
        : '';
      var huerfanos=Object.keys(pub).filter(function(id){
        if(id==='IMPERIO CONKAL') return false;
        for(var i=0;i<reales.length;i++){ if(String(reales[i].id)===id) return false; }
        return true;
      });
      var avisoHuerf = huerfanos.length
        ? '<div style="background:#fff8e1;border:1px solid #f0e0a0;border-radius:10px;padding:10px 12px;margin-bottom:12px;font-size:11px;color:#856404"><b>'+huerfanos.length+
          ' en el cat\\u00e1logo p\\u00fablico que ya no existen en la cartera:</b><br>'+esc(huerfanos.join(' \\u00b7 '))+
          '<br>Se borran solos en la pr\\u00f3xima sincronizaci\\u00f3n.</div>'
        : '';

      informe = ['CPM · revision de la cartera',
                 'cuenta: '+((user&&user.email)||'')+'  ·  admin: si',
                 reales.length+' propiedades · '+nExc+' exclusivas · '+nPubl+' publicables · '+
                 nEspejo+' en el catalogo · '+nCoord+' con coordenadas exactas',
                 ''].concat(informe);

      ov.innerHTML='<div class="cpm-sheet" style="padding:20px 18px 40px">'+
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'+
          '<h3 style="font-size:16px;font-weight:700;color:#1a2d42">Revisi\\u00f3n de la cartera</h3>'+
          '<button id="cpm-dg-x" style="background:#f0f4f8;border:none;border-radius:50%;width:34px;height:34px;font-size:18px;color:#5a6a7a">\\u2715</button>'+
        '</div>'+
        '<div style="font-size:11px;color:#7a8a9a;line-height:1.6;margin-bottom:14px">'+
          'Entraste como <b>'+esc((user&&user.email)||'')+'</b> y el sistema te reconoce como <b>administrador</b>. '+
          'Lo que sigue es lo que hay guardado de verdad en cada propiedad.'+
        '</div>'+
        avisoErr + avisoMalos + avisoHuerf +
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:6px;margin-bottom:14px">'+
          [[reales.length,'propiedades'],[nExc,'exclusivas'],[nPubl,'publicables'],[nEspejo,'en cat\\u00e1logo'],[nCoord,'con coords']]
            .map(function(p){ return '<div style="background:#f4f6f9;border-radius:10px;padding:9px 10px;text-align:center"><div style="font-size:17px;font-weight:700;color:#3d7ab5">'+p[0]+'</div><div style="font-size:9px;letter-spacing:1px;text-transform:uppercase;color:#7a8a9a">'+p[1]+'</div></div>'; }).join('')+
        '</div>'+
        (filas || '<div style="font-size:12px;color:#7a8a9a">La cartera est\\u00e1 vac\\u00eda.</div>')+
        '<button id="cpm-dg-copy" style="width:100%;margin-top:10px;background:#e8f2fb;color:#3d7ab5;border:none;padding:12px;border-radius:12px;font-size:12px;font-weight:700">\\ud83d\\udccb Copiar el informe como texto</button>'+
        '<textarea id="cpm-dg-txt" readonly style="width:100%;height:120px;margin-top:8px;font-size:10px;font-family:monospace;border:1px solid #e8ecf0;border-radius:10px;padding:8px;color:#5a6a7a"></textarea>'+
      '</div>';
      ov.querySelector('#cpm-dg-x').addEventListener('click',function(){ closeOverlay(ov); });
      var ta=ov.querySelector('#cpm-dg-txt');
      ta.value=informe.join('\\n');
      ov.querySelector('#cpm-dg-copy').addEventListener('click',function(){
        var b=ov.querySelector('#cpm-dg-copy');
        function ok(){ b.textContent='\\u2713 Copiado'; setTimeout(function(){ b.innerHTML='\\ud83d\\udccb Copiar el informe como texto'; },2500); }
        /* El portapapeles moderno no siempre existe dentro de un iframe;
           la seleccion del textarea funciona en todos lados. */
        try{
          if(navigator.clipboard && navigator.clipboard.writeText){
            navigator.clipboard.writeText(ta.value).then(ok,function(){ ta.select(); });
            return;
          }
        }catch(e3){}
        ta.select();
        try{ document.execCommand('copy'); ok(); }catch(e4){}
      });
    }
  }

"""
cambia("""  /* ===================== PDF (ventana de impresion) ===================== */""",
       DIAG + """  /* ===================== PDF (ventana de impresion) ===================== */""",
       'sitio del panel de revision')

# ══════════════════════════════════════════════════════════════════════
# 10. LA FICHA EN PDF LLEVA EL AVISO
#     El PDF es lo que sale de la oficina; el "no publicar" tiene que
#     viajar con el.
# ══════════════════════════════════════════════════════════════════════
cambia("""    '<div class="page"><div class="hdr"><img src="'+LOGO_W+'" class="logo" alt="CPM"><div class="badge">'+esc(t.tipo)+'</div></div>'+""",
       """    '<div class="page"><div class="hdr"><img src="'+LOGO_W+'" class="logo" alt="CPM"><div style="display:flex;gap:7px;align-items:center">'+
    (esExclusiva(t)?'<div class="badge" style="background:#8a1d1d">Exclusiva</div>':'')+
    '<div class="badge">'+esc(t.tipo)+'</div></div></div>'+""",
       'sello en el PDF')

# ══════════════════════════════════════════════════════════════════════
# 12. EL BOTON DE CERRAR, DEBAJO DE LA CABECERA DEL SITIO
#     Reportado: en el telefono el boton de cerrar la ficha queda casi
#     invisible y hay que girar el aparato para poder tocar el fondo.
#     Es el mismo defecto que ya se arreglo en el catalogo: la capa se
#     ancla a la parte visible del marco, pero esa parte se medía desde el
#     borde de la ventana (0), SIN descontar la cabecera fija del sitio,
#     que en movil ocupa los primeros ~64px. La cabecera de la ficha --
#     que es donde vive el boton -- quedaba justo debajo de ella.
#
#     Dos cosas, no una:
#       · la banda visible empieza debajo de la cabecera del sitio;
#       · la cabecera de la ficha es STICKY, asi que el boton sigue ahi
#         aunque se desplace el contenido. Antes se iba con el scroll.
# ══════════════════════════════════════════════════════════════════════
cambia("""  function banda(){
    if(!FRAME.el) return null;              /* fuera de iframe, fixed ya sirve */
    try{
      var r=FRAME.el.getBoundingClientRect(), ph=FRAME.win.innerHeight;
      var top=Math.max(0,-r.top);
      var bot=Math.min(r.height, ph-r.top);
      return {top:top, height:Math.max(220,bot-top)};
    }catch(e){ return null; }
  }""",
"""  var CABECERA=0;    /* alto de la cabecera fija del sitio, en px */
  function ventanaSitio(){
    try{ if(FRAME && FRAME.win) return FRAME.win; }catch(e){}
    return window;
  }
  function documentoSitio(){
    try{ var w=ventanaSitio(); if(w && w.document) return w.document; }catch(e){}
    return document;
  }
  /* Mide la cabecera fija del sitio. Ojo: hay que mirar el documento del
     SITIO, no el del bloque -- dentro del iframe no hay ninguna cabecera
     fija y siempre mediria 0, que es justo lo que pasaba. */
  function medirCabecera(){
    var alto=0;
    try{
      var w=ventanaSitio(), doc=documentoSitio();
      var nodos=doc.body ? doc.body.children : [];
      var anchoVentana=w.innerWidth||window.innerWidth||360;
      for(var i=0;i<nodos.length;i++){
        var e=nodos[i];
        var cs=w.getComputedStyle ? w.getComputedStyle(e) : getComputedStyle(e);
        if(cs.position!=='fixed' && cs.position!=='sticky') continue;
        if(cs.display==='none' || cs.visibility==='hidden') continue;
        var r=e.getBoundingClientRect();
        /* Pegada arriba, ancha y de alto razonable: eso es una cabecera.
           Lo que no cumpla las tres cosas puede ser un boton flotante. */
        if(r.top<=2 && r.bottom>alto && r.bottom<260 && r.width>anchoVentana*0.5) alto=r.bottom;
      }
    }catch(e){}
    CABECERA=Math.round(alto);
    return CABECERA;
  }
  function banda(){
    if(!FRAME.el) return null;              /* fuera de iframe, fixed ya sirve */
    try{
      var r=FRAME.el.getBoundingClientRect(), ph=FRAME.win.innerHeight;
      /* La banda empieza DEBAJO de la cabecera del sitio: si empezara en el
         borde de la ventana, la cabecera de la ficha -- y con ella el boton
         de cerrar -- quedaria tapada. */
      var top=Math.max(0, CABECERA-r.top);
      var bot=Math.min(r.height, ph-r.top);
      /* Si descontarla deja una banda demasiado corta, se prefiere mostrar
         la ficha entera aunque roce la cabecera. */
      if(bot-top<300) top=Math.max(0,-r.top);
      return {top:top, height:Math.max(220,bot-top)};
    }catch(e){ return null; }
  }""", 'banda con cabecera')

# La cabecera se mide al abrir cada capa: el sitio puede haberla cambiado
# de alto al desplazarse (muchas se encogen).
cambia("""  function mkOverlay(z){
    var ov=document.createElement('div');
    ov.className='cpm-ov cpm-ov-live';
    ov.style.zIndex=(z||2147483000);
    document.body.appendChild(ov);
    anclados.push(ov);
    anclar(ov);                       /* centrado en la PANTALLA, no en el iframe */
    document.body.style.overflow='hidden';
    return ov;
  }
  function closeOverlay(ov){
    var i=anclados.indexOf(ov); if(i>=0) anclados.splice(i,1);
    if(ov&&ov.parentNode) ov.parentNode.removeChild(ov);
    if(!document.querySelector('.cpm-ov-live')) document.body.style.overflow='';
  }""",
"""  /* ─────────────────────────────────────────────────────────
     Con una capa abierta, el SITIO seguia desplazandose por detras: se
     movia el fondo mientras la ficha se reanclaba, y se perdia el sitio
     donde se estaba. Se bloquea el desplazamiento del documento del
     sitio, no el del bloque -- el del bloque no se desplaza nunca.
     El valor anterior se guarda y se restaura al cerrar; y por si algo
     fallara, el latido de anclar() lo devuelve en cuanto no queda
     ninguna capa. Dejar un sitio sin poder desplazarse seria peor que
     el problema que esto resuelve.
     ───────────────────────────────────────────────────────── */
  var scrollGuardado=null;
  function trabarSitio(){
    if(scrollGuardado!==null) return;
    try{
      var d=documentoSitio(), e=d.documentElement;
      scrollGuardado={el:e, valor:e.style.overflow};
      e.style.overflow='hidden';
    }catch(e2){ scrollGuardado=null; }
  }
  function destrabarSitio(){
    if(!scrollGuardado) { scrollGuardado=null; return; }
    try{ scrollGuardado.el.style.overflow=scrollGuardado.valor||''; }catch(e){}
    scrollGuardado=null;
  }
  function mkOverlay(z){
    var ov=document.createElement('div');
    ov.className='cpm-ov cpm-ov-live';
    ov.style.zIndex=(z||2147483000);
    document.body.appendChild(ov);
    anclados.push(ov);
    medirCabecera();                  /* antes de anclar, no despues */
    anclar(ov);                       /* centrado en la PANTALLA, no en el iframe */
    document.body.style.overflow='hidden';
    trabarSitio();
    return ov;
  }
  function closeOverlay(ov){
    var i=anclados.indexOf(ov); if(i>=0) anclados.splice(i,1);
    if(ov&&ov.parentNode) ov.parentNode.removeChild(ov);
    if(!document.querySelector('.cpm-ov-live')){
      document.body.style.overflow='';
      destrabarSitio();
    }
  }
  /* Escape cierra la capa de encima. No estaba, y en el ordenador es lo
     primero que se intenta. */
  function capaDeEncima(){
    var todas=document.querySelectorAll('.cpm-ov-live');
    return todas.length ? todas[todas.length-1] : null;
  }
  (function(){
    function alTeclado(ev){
      if(ev.key!=='Escape' && ev.key!=='Esc') return;
      var ov=capaDeEncima();
      if(ov) closeOverlay(ov);
    }
    document.addEventListener('keydown',alTeclado);
    try{ if(FRAME.win) FRAME.win.document.addEventListener('keydown',alTeclado); }catch(e){}
  })();""", 'mkOverlay y closeOverlay')

# Red de seguridad: si no queda ninguna capa, el sitio vuelve a moverse.
cambia("""    function ping(){ for(var i=0;i<anclados.length;i++) anclar(anclados[i]); }""",
       """    function ping(){
      for(var i=0;i<anclados.length;i++) anclar(anclados[i]);
      if(!anclados.length && scrollGuardado) destrabarSitio();
    }""", 'red de seguridad del desplazamiento')

# ── La cabecera de la ficha, pegada arriba y con un boton que se ve ──
cambia("""        '<div style="display:flex;justify-content:center;padding:12px 16px 4px;position:relative"><div style="width:40px;height:4px;background:#d0d8e0;border-radius:2px"></div>'+
          '<button id="cpm-f-x" style="position:absolute;top:12px;right:14px;background:#f0f4f8;border:none;border-radius:50%;width:34px;height:34px;color:#5a6a7a;font-size:18px;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,.12)">✕</button></div>'+""",
       """        '<div class="cpm-sheet-top"><div class="asa"></div>'+
          '<button id="cpm-f-x" class="cpm-x" type="button" aria-label="Cerrar">✕</button></div>'+""",
       'cabecera de la ficha')

cambia("""/* En movil vuelve a ser hoja inferior, que ahi si es lo correcto */
@media(max-width:600px){
  .cpm-ov{ align-items:flex-end; padding:0; }
  .cpm-ov .cpm-sheet{ max-width:100%; border-radius:22px 22px 0 0; }
}""",
"""/* En movil vuelve a ser hoja inferior, que ahi si es lo correcto */
@media(max-width:600px){
  .cpm-ov{ align-items:flex-end; padding:0; }
  .cpm-ov .cpm-sheet{ max-width:100%; border-radius:22px 22px 0 0; }
}
/* ── Cabecera de la hoja ──────────────────────────────────────────
   PEGADA (sticky) a proposito: antes el boton de cerrar se iba con el
   desplazamiento y, si la banda visible no descontaba la cabecera del
   sitio, no habia forma de alcanzarlo -- el defecto reportado. Ahora se
   queda siempre a la vista, encima del contenido.
   El fondo es opaco: sin el, las fotos se veian pasar por debajo. */
.cpm-ov .cpm-sheet-top{
  position:sticky; top:0; z-index:5;
  display:flex; align-items:center; justify-content:center;
  padding:10px 14px; background:#fff;
  border-radius:22px 22px 0 0;
  box-shadow:0 1px 0 rgba(26,45,66,.08);
}
.cpm-ov .cpm-sheet-top .asa{
  width:44px; height:4px; background:#d0d8e0; border-radius:2px;
}
.cpm-ov .cpm-x{
  position:absolute; top:8px; right:10px;
  width:40px; height:40px; border-radius:50%;
  background:#eef2f7; border:1px solid #dde4ec; color:#3a4a5a;
  font-size:19px; line-height:1; display:flex; align-items:center; justify-content:center;
  cursor:pointer; box-shadow:0 2px 8px rgba(26,45,66,.18);
  font-family:'Montserrat',sans-serif;
}
.cpm-ov .cpm-x:hover{ background:#e2e8f0; color:#1a2d42 }
.cpm-ov .cpm-x:active{ transform:scale(.94) }
@media(max-width:600px){
  /* 44px es el minimo con el que un dedo acierta sin mirar. */
  .cpm-ov .cpm-x{ width:44px; height:44px; top:7px; right:10px; font-size:20px }
  .cpm-ov .cpm-sheet-top{ padding:12px 14px }
}""", 'CSS de la cabecera de la hoja')

# ══════════════════════════════════════════════════════════════════════
# 13. EL PDF
#     Reportado: no se descarga bien, y el boton de ubicacion no abre.
#
#     Que estaba mal, por partes:
#     a) window.open('') devuelve null si el navegador bloquea la ventana
#        -- y dentro de un iframe con sandbox pasa siempre --. El codigo
#        hacia `if(!w) return;`: no pasaba nada y nadie se enteraba.
#     b) Se imprimia en window.onload, que espera a TODAS las fotos. Una
#        foto que no llega deja la ventana abierta sin imprimir nunca.
#     c) La ubicacion era un enlace SIN target: al pulsarlo, la ventana
#        de la ficha se iba a Google Maps y se perdia el documento. Y en
#        un PDF ya guardado, muchos visores no respetan los enlaces.
#        Ahora, ademas del enlace, van la direccion y las coordenadas
#        ESCRITAS: eso se lee, se copia y se teclea aunque el enlace no
#        funcione.
#     d) Las direcciones de las fotos se metian sin escapar.
# ══════════════════════════════════════════════════════════════════════
cambia("""  function generarPDF(t, asesorNombre, asesorTel){
    var w=window.open('','_blank'); if(!w) return;
    var precio=t.precio_total||t.precio;""",
"""  /* Manda el documento a la impresora. Tres caminos, del mejor al que
     siempre funciona; el primero que arranca gana.
       1. Ventana nueva con el documento en una direccion blob:.
       2. Marco oculto en esta misma pagina, por si las ventanas nuevas
          estan bloqueadas -- dentro de un iframe con sandbox lo estan
          siempre, y antes eso dejaba el boton sin hacer NADA.
       3. La hoja en pantalla con su boton, si el navegador tampoco deja
          imprimir por guion.

     Por que blob: y no la receta habitual de abrir una ventana en blanco
     y escribirle el documento: MEDIDO, en esa ventana las fotos no se
     llegan a pedir siquiera -- ni una peticion --, asi que la ficha salia
     impresa sin ninguna imagen. Con una direccion blob: el documento se
     carga de verdad y las fotos entran. */
  function haceBlob(html){
    try{
      var B = window.Blob, U = window.URL || window.webkitURL;
      if(!B || !U || !U.createObjectURL) return null;
      return U.createObjectURL(new B([html], {type:'text/html;charset=utf-8'}));
    }catch(e){ return null; }
  }
  function sueltaBlob(url){
    if(!url) return;
    /* Tarde: revocarla mientras el navegador todavia imprime deja la
       ventana en blanco. */
    setTimeout(function(){
      try{ (window.URL||window.webkitURL).revokeObjectURL(url); }catch(e){}
    }, 300000);
  }
  /* Espera a que el documento de la ventana termine de cargar. Con tope,
     porque una ventana que no responde no puede colgar el boton. */
  function cuandoCargue(ven, cb){
    var t0=Date.now(), hecho=false;
    function ya(){ if(hecho) return; hecho=true; cb(); }
    (function ver(){
      if(hecho) return;
      var rs='';
      try{ rs = ven.document && ven.document.readyState; }
      catch(e){ ya(); return; }        /* no se puede mirar: a imprimir */
      if(rs==='complete' || Date.now()-t0>4000){ ya(); return; }
      setTimeout(ver,120);
    })();
  }
  function imprimir(html, titulo, alSalir){
    function fin(){ if(alSalir){ var f=alSalir; alSalir=null; try{ f(); }catch(e){} } }
    var url = haceBlob(html);

    /* 1. Ventana nueva. */
    if(url){
      var w=null;
      try{ w=window.open(url,'_blank'); }catch(e){ w=null; }
      if(w){
        cuandoCargue(w, function(){
          try{ w.document.title=titulo; }catch(e2){}
          alImprimir(w, function(){
            try{ w.focus(); w.print(); }catch(e3){}
            fin();
          });
        });
        sueltaBlob(url);
        return;
      }
    }

    /* 2. Marco oculto. */
    try{
      var m=document.createElement('iframe');
      m.setAttribute('aria-hidden','true');
      m.style.cssText='position:absolute;width:1px;height:1px;left:-9999px;top:0;border:0';
      document.body.appendChild(m);
      function alListo(){
        try{ m.contentWindow.document.title=titulo; }catch(e){}
        alImprimir(m.contentWindow, function(){
          var ok=false;
          try{ m.contentWindow.focus(); m.contentWindow.print(); ok=true; }catch(e6){}
          fin();
          /* El marco se retira tarde a proposito: quitarlo con el dialogo
             de impresion abierto lo cancela en algunos navegadores. */
          setTimeout(function(){ try{ m.parentNode.removeChild(m); }catch(e7){} }, 300000);
          if(!ok) verEnPantalla(html);
        });
      }
      if(url){
        m.onload=alListo;
        m.src=url;
        sueltaBlob(url);
      } else {
        var d=m.contentWindow.document;
        d.open(); d.write(html); d.close();
        setTimeout(alListo,60);
      }
      return;
    }catch(e8){}

    /* 3. A la vista, y que la imprima quien pueda. */
    sueltaBlob(url);
    fin();
    verEnPantalla(html);
  }
  /* Espera a que carguen las fotos y entonces imprime.
     Se escuchan load y error de cada foto en vez de mirar `complete` en
     un bucle: una peticion que se queda colgada nunca pone complete a
     true, y con el bucle habia que agotar el tope entero. Medido: con una
     foto que no llegaba, el dialogo de impresion tardaba OCHO SEGUNDOS en
     aparecer -- que desde fuera es exactamente "el PDF no se descarga".
     El tope se queda en 3,5 s: una foto que no ha llegado para entonces
     no va a mejorar la ficha, y es mejor imprimirla sin ella. */
  function alImprimir(ven, hacer){
    var listo=false, tope=null;
    function ya(){
      if(listo) return;
      listo=true;
      if(tope) clearTimeout(tope);
      hacer();
    }
    var imgs;
    try{ imgs=Array.prototype.slice.call(ven.document.images||[]); }
    catch(e){ ya(); return; }
    var faltan=0;
    imgs.forEach(function(im){
      if(im.complete) return;
      faltan++;
      function fin2(){
        im.removeEventListener('load',fin2);
        im.removeEventListener('error',fin2);
        if(--faltan<=0) setTimeout(ya,80);
      }
      im.addEventListener('load',fin2);
      im.addEventListener('error',fin2);
    });
    if(!faltan){ setTimeout(ya,80); return; }
    tope=setTimeout(ya,3500);
  }
  /* Ultimo recurso visible: la ficha dentro de una capa, con su boton. */
  function verEnPantalla(html){
    var ov=mkOverlay(2147483600);
    ov.innerHTML=
      '<div class="cpm-sheet" style="max-width:820px;display:flex;flex-direction:column">'+
        '<div class="cpm-sheet-top" style="justify-content:space-between;padding:12px 16px">'+
          '<b style="font-size:13px;color:#1a2d42">Ficha lista para imprimir</b>'+
          '<button id="cpm-pr-x" class="cpm-x" type="button" aria-label="Cerrar">\u2715</button>'+
        '</div>'+
        '<div style="padding:0 14px 12px;font-size:12px;color:#5a6a7a;line-height:1.6">'+
          'Tu navegador no dej\u00f3 abrir la ventana de impresi\u00f3n. Usa el bot\u00f3n de abajo, '+
          'o el men\u00fa <b>Compartir \u2192 Imprimir</b> del navegador, y elige '+
          '<b>Guardar como PDF</b>.'+
        '</div>'+
        '<iframe id="cpm-pr-m" style="width:100%;flex:1;min-height:340px;border:1px solid #e8ecf0;border-radius:12px;background:#fff"></iframe>'+
        '<button id="cpm-pr-go" class="cpm-btn-main" style="margin:12px 0 4px">\u2399 Imprimir o guardar como PDF</button>'+
      '</div>';
    var m=ov.querySelector('#cpm-pr-m');
    try{ var d=m.contentWindow.document; d.open(); d.write(html); d.close(); }catch(e){}
    ov.querySelector('#cpm-pr-x').addEventListener('click',function(){ closeOverlay(ov); });
    ov.querySelector('#cpm-pr-go').addEventListener('click',function(){
      try{ m.contentWindow.focus(); m.contentWindow.print(); }
      catch(e){ try{ window.print(); }catch(e2){} }
    });
    ov.addEventListener('click',function(e){ if(e.target===ov) closeOverlay(ov); });
  }

  function generarPDF(t, asesorNombre, asesorTel, alSalir){
    var precio=t.precio_total||t.precio;""",
       'imprimir con respaldos')

cambia("""    var fotosHTML=(t.fotos&&t.fotos.length>0)?'<div class="sec" style="margin-bottom:10px">Fotografías</div><div class="foto-grid">'+t.fotos.slice(0,6).map(function(f){return '<img src="'+f+'" alt="foto">'}).join('')+'</div>':'';""",
       """    var fotosHTML=(t.fotos&&t.fotos.length>0)?'<div class="sec" style="margin-bottom:10px">Fotografías</div><div class="foto-grid">'+t.fotos.slice(0,6).map(function(f){return '<img src="'+esc(f)+'" alt="foto">'}).join('')+'</div>':'';
    /* La ubicacion, escrita ademas de enlazada: un PDF guardado y
       reenviado pierde los enlaces en muchos visores, y entonces el
       cliente se queda sin saber donde esta el predio. */
    var cGeo=coordsDe(t);
    var urlMaps=(t.ubicacion_maps&&/^https?:/i.test(t.ubicacion_maps))?t.ubicacion_maps:'';
    var urlGeo=cGeo?('https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(cGeo[0]+','+cGeo[1])):'';
    var urlIr=urlGeo||urlMaps;
    var ubicacionHTML='';
    if(urlIr){
      ubicacionHTML='<div class="sec">Ubicación</div>'+
        '<a href="'+esc(urlIr)+'" class="cta-ubicacion" target="_blank" rel="noopener">🗺 Abrir la ubicación en Google Maps</a>'+
        '<div class="ubi-txt">'+
          (cGeo?'<div><b>Coordenadas:</b> '+esc(txtCoords(cGeo[0],cGeo[1]))+'</div>':'')+
          '<div><b>Enlace:</b> '+esc(urlIr)+'</div>'+
        '</div>';
    }""",
       'ubicacion del PDF')

cambia("""    '.cta-ubicacion{display:inline-block;background:#3d7ab5;color:#fff;padding:9px 20px;border-radius:8px;font-size:11px;font-weight:700;text-decoration:none;letter-spacing:1px;margin-bottom:14px}'+""",
       """    '.cta-ubicacion{display:inline-block;background:#3d7ab5;color:#fff;padding:9px 20px;border-radius:8px;font-size:11px;font-weight:700;text-decoration:none;letter-spacing:1px;margin-bottom:8px}'+
    '.ubi-txt{font-size:10px;color:#5a6a7a;line-height:1.7;margin-bottom:14px;word-break:break-all}'+
    '.ubi-txt b{color:#1a2d42}'+"""
       , 'CSS de la ubicacion escrita')

cambia("""    ((t.ubicacion_maps&&/^http/.test(t.ubicacion_maps))?'<div class="sec">Ubicación</div><a href="'+esc(t.ubicacion_maps)+'" class="cta-ubicacion">🗺 Ver Ubicación en Google Maps</a>':'')+
    '</div><div class="foot">""",
       """    ubicacionHTML+
    '</div><div class="foot">""", 'sitio de la ubicacion en el PDF')

cambia("""    '<scr'+'ipt>document.title='+JSON.stringify(nombreArchivo)+';window.onload=function(){window.print()};</scr'+'ipt></body></html>';
    w.document.write(html); w.document.close();
  }""",
       """    '<scr'+'ipt>document.title='+JSON.stringify(nombreArchivo)+';</scr'+'ipt></body></html>';
    /* La impresion NO se dispara desde dentro del documento: se hace desde
       aqui, cuando las fotos ya estan o cuando se agota el tiempo. Antes
       iba en window.onload, que espera a todas las fotos sin limite. */
    imprimir(html, nombreArchivo, alSalir);
  }""", 'disparo de la impresion')

# El nombre del archivo es el titulo del documento: los caracteres que no
# valen en un nombre de archivo se cambian aqui, no en el navegador.
cambia("""    var nombreArchivo=[t.nombre,t.id,asesorNombre].filter(Boolean).join(' - ');""",
       """    var nombreArchivo=[t.nombre,t.id,asesorNombre].filter(Boolean).join(' - ')
      .replace(/[\\/:*?"<>|]+/g,' ').replace(/\s+/g,' ').trim();""",
       'nombre del archivo')

# ══════════════════════════════════════════════════════════════════════
# 14. EL ENLACE DE UBICACION DE LA FICHA
#     Un target="_blank" dentro de un iframe con sandbox no abre nada. Se
#     intenta abrir, y si el navegador lo impide se navega la ventana
#     completa -- que es lo que el usuario esperaba de todas formas.
# ══════════════════════════════════════════════════════════════════════
cambia("""    var maps=(t.ubicacion_maps&&/^http/.test(t.ubicacion_maps))?'<a href="'+esc(t.ubicacion_maps)+'" target="_blank" rel="noreferrer" style="display:flex;align-items:center;gap:10px;background:linear-gradient(135deg,#3d7ab5,#2d5f8f);border-radius:12px;padding:14px 18px;text-decoration:none;color:#fff;margin-bottom:16px;font-size:14px;font-weight:700"><span style="font-size:22px">🗺</span><span>Ver Ubicación</span><span style="margin-left:auto;font-size:18px">→</span></a>':'';""",
       """    var cFicha=coordsDe(t);
    var urlFicha=(t.ubicacion_maps&&/^http/.test(t.ubicacion_maps)) ? t.ubicacion_maps
      : (cFicha?('https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(cFicha[0]+','+cFicha[1])):'');
    var maps=urlFicha?'<a id="cpm-f-maps" href="'+esc(urlFicha)+'" target="_blank" rel="noopener" style="display:flex;align-items:center;gap:10px;background:linear-gradient(135deg,#3d7ab5,#2d5f8f);border-radius:12px;padding:14px 18px;text-decoration:none;color:#fff;margin-bottom:16px;font-size:14px;font-weight:700"><span style="font-size:22px">🗺</span><span>Ver Ubicación</span><span style="margin-left:auto;font-size:18px">→</span></a>':'';""",
       'enlace de maps de la ficha')

cambia("""    var bWa=ov.querySelector('#cpm-f-wa');
    if(bWa) bWa.addEventListener('click',function(){ window.open(waHref,'_blank'); });""",
       """    var bWa=ov.querySelector('#cpm-f-wa');
    if(bWa) bWa.addEventListener('click',function(){ abrirFuera(waHref); });
    var bMaps=ov.querySelector('#cpm-f-maps');
    if(bMaps) bMaps.addEventListener('click',function(ev){
      /* Si el navegador deja abrir pestaña, que la abra el enlace solo.
         Si no -- iframe con sandbox --, se navega la ventana completa. */
      if(abrirFuera(urlFicha,true)) return;
      ev.preventDefault();
      try{ window.top.location.href=urlFicha; }catch(e){ location.href=urlFicha; }
    });""", 'apertura del enlace de maps')

cambia("""  /* ===================== OVERLAY util ===================== */""",
       """  /* Abre una direccion fuera del bloque. Dentro de un iframe con
     sandbox, window.open devuelve null y target="_blank" no hace nada:
     entonces se navega la ventana completa. Devuelve si lo consiguio. */
  function abrirFuera(url, soloProbar){
    var w=null;
    try{ w=window.open(url,'_blank','noopener'); }catch(e){ w=null; }
    if(w) return true;
    if(soloProbar) return false;
    try{ window.top.location.href=url; return true; }catch(e2){}
    try{ location.href=url; return true; }catch(e3){}
    return false;
  }

  /* ===================== OVERLAY util ===================== */""",
       'abrirFuera')

# ══════════════════════════════════════════════════════════════════════
# 15. INTERFAZ
# ══════════════════════════════════════════════════════════════════════
# a) El velo llevaba backdrop-filter, que cuesta fotogramas incluso fuera
#    de pantalla (ya medido en otros bloques de este mismo sitio). Se
#    quita y se oscurece el velo, que se ve igual de bien y no cuesta.
cambia("""  background:rgba(26,45,66,.7); -webkit-backdrop-filter:blur(6px); backdrop-filter:blur(6px);""",
       """  /* Sin backdrop-filter: cuesta fotogramas hasta cuando la capa no se ve.
     Un velo mas oscuro separa igual de bien y es gratis. */
  background:rgba(15,26,40,.82);""", 'velo sin desenfoque')

# b) La ficha repetia la superficie: "SUPERFICIE 256 m²" y "M² 256" dicen
#    lo mismo. Solo se muestra el m² suelto si aporta algo (cuando la
#    superficie se expresa en hectareas).
cambia("""    if(t.dimensiones_m2>0) specs.push(['m²',(t.dimensiones_m2).toLocaleString('es-MX')]);""",
       """    /* El m² suelto solo cuando la superficie va en hectareas: si no,
       repetia la misma cifra dos veces en dos cuadros contiguos. */
    if(t.dimensiones_m2>0 && t.hectareas>=1) specs.push(['m² exactos',(t.dimensiones_m2).toLocaleString('es-MX')]);
    if(coordsDe(t)) specs.push(['Coordenadas','Registradas']);""",
       'superficie repetida')

# c) Tarjetas alcanzables con el teclado y fotos que no se cargan todas de
#    golpe en el movil.
cambia("""      return '<div class="cpm-card'+(t._premium?' premium':'')+'" data-id="'+esc(t.id)+'">'+
        '<div class="ph">'+
          (hasFotos?'<img class="cover" src="'+esc(t.fotos[0])+'" alt="">':'<img class="logo" src="'+LOGO_AZUL+'" alt="CPM">')+""",
       """      return '<div class="cpm-card'+(t._premium?' premium':'')+'" data-id="'+esc(t.id)+
             '" tabindex="0" role="button" aria-label="'+esc((t.nombre||t.id)+' · '+(t.ciudad||''))+'">'+
        '<div class="ph">'+
          (hasFotos?'<img class="cover" loading="lazy" src="'+esc(t.fotos[0])+'" alt="">':'<img class="logo" src="'+LOGO_AZUL+'" alt="CPM">')+""",
       'tarjeta accesible')

cambia("""    grid.querySelectorAll('.cpm-card').forEach(function(card){
      card.addEventListener('click',function(){
        var t=terrenos.find(function(x){return x.id===card.getAttribute('data-id')});
        if(t) openFicha(t);
      });
    });""",
       """    grid.querySelectorAll('.cpm-card').forEach(function(card){
      function abrir(){
        var t=terrenos.find(function(x){return x.id===card.getAttribute('data-id')});
        if(t) openFicha(t);
      }
      card.addEventListener('click',abrir);
      card.addEventListener('keydown',function(ev){
        if(ev.key==='Enter' || ev.key===' '){ ev.preventDefault(); abrir(); }
      });
    });""", 'tarjeta con teclado')

# d) Blancos de toque. Los botones de la barra median 26px de alto: en un
#    telefono eso se falla. 44px es el minimo con el que un dedo acierta.
cambia("""@media(max-width:600px){
  #cpm-portafolio .cpm-grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;padding:14px}""",
       """@media(max-width:600px){
  #cpm-portafolio .cpm-mini{padding:10px 14px;font-size:12px;min-height:40px;display:inline-flex;align-items:center}
  #cpm-portafolio .cpm-bar{gap:8px 10px;row-gap:8px}
  #cpm-portafolio .cpm-pill{padding:9px 14px;min-height:38px;display:inline-flex;align-items:center}
  #cpm-portafolio .cpm-grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;padding:14px}""",
       'blancos de toque en movil')

cambia("""<button data-rm="'+i+'" style="position:absolute;top:2px;right:2px;background:rgba(231,76,60,.9);border:none;border-radius:50%;width:20px;height:20px;color:#fff;font-size:10px">✕</button>""",
       """<button data-rm="'+i+'" aria-label="Quitar foto" style="position:absolute;top:3px;right:3px;background:rgba(231,76,60,.95);border:none;border-radius:50%;width:28px;height:28px;color:#fff;font-size:13px;line-height:1;box-shadow:0 1px 4px rgba(0,0,0,.3)">✕</button>""",
       'boton de quitar foto')

# e) El icono de la lupa se centraba con un ajuste a mano (50% + 8px) que
#    solo cuadra con un relleno concreto: en movil el relleno cambia y el
#    icono se descuadra. Se centra respecto al campo, no al contenedor.
cambia("""#cpm-portafolio .cpm-search-wrap{padding:16px 24px 0;position:relative}
#cpm-portafolio .cpm-search-wrap .ico{position:absolute;left:38px;top:calc(50% + 8px);transform:translateY(-50%);color:#a0b0c0}""",
       """#cpm-portafolio .cpm-search-wrap{padding:16px 24px 0}
/* La caja es la referencia del icono, no el contenedor con relleno: asi
   no hay que compensar a mano cada vez que cambia el relleno. */
#cpm-portafolio .cpm-search-caja{position:relative}
#cpm-portafolio .cpm-search-wrap .ico{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:#a0b0c0;pointer-events:none;line-height:1}""",
       'CSS de la lupa')

cambia("""      '<div class="cpm-search-wrap"><span class="ico">🔍</span>'+
        '<input id="cpm-q" class="cpm-search" placeholder="Buscar por ciudad, ID, descripción..." value="'+esc(q)+'"></div>'+""",
       """      '<div class="cpm-search-wrap"><div class="cpm-search-caja"><span class="ico" aria-hidden="true">🔍</span>'+
        '<input id="cpm-q" class="cpm-search" type="search" aria-label="Buscar propiedades" placeholder="Buscar por ciudad, ID, descripción..." value="'+esc(q)+'"></div></div>'+""",
       'maquetacion de la lupa')

cambia("""  #cpm-portafolio .cpm-search-wrap{padding:14px 14px 0}
  #cpm-portafolio .cpm-search-wrap .ico{left:28px}""",
       """  #cpm-portafolio .cpm-search-wrap{padding:14px 14px 0}""",
       'lupa en movil')

# f) La galeria: flechas del teclado, Escape y botones mas grandes en el
#    telefono. Y se dice en que foto se va.
cambia("""      ov.querySelector('#cpm-g-x').addEventListener('click',function(){ closeOverlay(ov); });
      if(fotos.length>1){
        ov.querySelector('#cpm-g-prev').addEventListener('click',function(){ idx=(idx-1+fotos.length)%fotos.length; draw(); });
        ov.querySelector('#cpm-g-next').addEventListener('click',function(){ idx=(idx+1)%fotos.length; draw(); });
        ov.querySelectorAll('i[data-i]').forEach(function(d){ d.addEventListener('click',function(){ idx=+d.getAttribute('data-i'); draw(); }); });
      }
    }
    draw();""",
       """      ov.querySelector('#cpm-g-x').addEventListener('click',function(){ closeOverlay(ov); });
      if(fotos.length>1){
        ov.querySelector('#cpm-g-prev').addEventListener('click',function(){ mover(-1); });
        ov.querySelector('#cpm-g-next').addEventListener('click',function(){ mover(1); });
        ov.querySelectorAll('i[data-i]').forEach(function(d){ d.addEventListener('click',function(){ idx=+d.getAttribute('data-i'); draw(); }); });
      }
    }
    function mover(p){ idx=(idx+p+fotos.length)%fotos.length; draw(); }
    /* Flechas del teclado: en el ordenador es lo natural, y no estaba.
       El listener se quita al cerrar la capa. */
    function alTeclado(ev){
      if(!ov.parentNode){ quitar(); return; }
      if(ev.key==='ArrowLeft'){ ev.preventDefault(); mover(-1); }
      else if(ev.key==='ArrowRight'){ ev.preventDefault(); mover(1); }
    }
    function quitar(){
      document.removeEventListener('keydown',alTeclado);
      try{ if(FRAME.win) FRAME.win.document.removeEventListener('keydown',alTeclado); }catch(e){}
    }
    document.addEventListener('keydown',alTeclado);
    try{ if(FRAME.win) FRAME.win.document.addEventListener('keydown',alTeclado); }catch(e){}
    draw();""", 'galeria con teclado')

# ── El aviso en el boton mientras se prepara la ficha ────────────────
#    Preparar el documento y esperar a las fotos lleva un momento. Sin
#    decir nada, ese momento se lee como "no pasó nada" y se vuelve a
#    pulsar. El boton lo dice y se desactiva mientras tanto.
cambia("""  function descargarFicha(t){
    var d=datosAsesor();
    if(d){ generarPDF(t, d.nombre, d.telefono); return; }
    pedirDatosAsesor(function(n,tel){ generarPDF(t, n, tel); });
  }""",
"""  function descargarFicha(t, alSalir){
    var d=datosAsesor();
    if(d){ generarPDF(t, d.nombre, d.telefono, alSalir); return; }
    pedirDatosAsesor(function(n,tel){ generarPDF(t, n, tel, alSalir); });
  }""", 'descargarFicha con aviso')

cambia("""    var bPdf=ov.querySelector('#cpm-f-pdf');
    if(bPdf) bPdf.addEventListener('click',function(){ descargarFicha(t); });""",
"""    var bPdf=ov.querySelector('#cpm-f-pdf');
    if(bPdf) bPdf.addEventListener('click',function(){
      var antes=bPdf.innerHTML;
      bPdf.disabled=true; bPdf.style.opacity='.72'; bPdf.innerHTML='\u23f3 Preparando la ficha\u2026';
      function soltar(){
        if(!bPdf) return;
        bPdf.disabled=false; bPdf.style.opacity=''; bPdf.innerHTML=antes;
      }
      /* Se suelta al despachar la impresion, y en todo caso a los 6 s:
         el boton no se puede quedar bloqueado pase lo que pase. */
      var red=setTimeout(soltar,6000);
      descargarFicha(t, function(){ clearTimeout(red); soltar(); });
    });""", 'boton de PDF con aviso')

# ══════════════════════════════════════════════════════════════════════
# 16. LA FICHA SE RECORTABA AL FILTRAR (escritorio)
#     Una capa dentro de un iframe NO puede pintar fuera del iframe: es
#     un limite del navegador, no del CSS. Y el alto del marco lo fija el
#     constructor segun lo que mide el bloque, asi que al filtrar y
#     quedar dos tarjetas el marco encoge -- medido: de 749px a 520 -- y
#     la ficha se recorta a esos 520 aunque la pantalla tenga 860.
#
#     La unica salida es agrandar el marco. Mientras haya una ventana
#     abierta, el propio bloque pone su marco a pantalla completa EN EL
#     SITIO (position:fixed, alto de la ventana) y al cerrar lo deja
#     exactamente como estaba. Se conservan izquierda y ancho para que el
#     contenido de detras no se recoloque, y el hueco que deja el marco
#     se sujeta con la altura del contenedor para que la pagina no pegue
#     un salto.
#
#     Si algun contenedor del sitio tiene transform o filter, 'fixed' se
#     ancla a EL y no a la ventana. Por eso, despues de aplicarlo, se
#     comprueba que el marco quedo de verdad donde se pedia; si no, se
#     deshace y se sigue con el comportamiento de antes.
# ══════════════════════════════════════════════════════════════════════
cambia("""  var anclados=[];""",
"""  /* Marco a pantalla completa mientras hay una ventana abierta. */
  var pantalla=null;
  function alturaSitio(){
    var h=0;
    try{ h=(FRAME.win&&FRAME.win.innerHeight)||window.innerHeight; }catch(e){ h=window.innerHeight; }
    return h||600;
  }
  function aPantallaCompleta(){
    if(pantalla) return true;
    if(!FRAME.el) return false;
    var el=FRAME.el, padre=el.parentElement;
    var r, guarda;
    try{
      r=el.getBoundingClientRect();
      guarda={css:el.style.cssText, padre:padre, padreAlto:padre?padre.style.height:''};
      /* El hueco se sujeta antes de sacar el marco del flujo. */
      if(padre) padre.style.height=Math.round(r.height)+'px';
      var s=el.style;
      s.setProperty('position','fixed','important');
      s.setProperty('top','0','important');
      s.setProperty('bottom','auto','important');
      /* Izquierda y ancho como estaban: asi el contenido de detras no se
         recoloca y al cerrar no hay salto. */
      s.setProperty('left',Math.round(r.left)+'px','important');
      s.setProperty('width',Math.round(r.width)+'px','important');
      s.setProperty('height',alturaSitio()+'px','important');
      s.setProperty('max-height','none','important');
      s.setProperty('min-height','0','important');
      s.setProperty('z-index','2147483000','important');
      var r2=el.getBoundingClientRect();
      if(Math.abs(r2.top)>2 || Math.abs(r2.height-alturaSitio())>4){
        throw new Error('no se ancla a la ventana');
      }
      pantalla=guarda;
      return true;
    }catch(e){
      try{ if(guarda){ el.style.cssText=guarda.css; } }catch(e2){}
      try{ if(guarda&&guarda.padre){ guarda.padre.style.height=guarda.padreAlto||''; } }catch(e3){}
      pantalla=null;
      return false;
    }
  }
  function salirPantallaCompleta(){
    if(!pantalla) return;
    var g=pantalla; pantalla=null;
    try{ FRAME.el.style.cssText=g.css; }catch(e){}
    try{ if(g.padre) g.padre.style.height=g.padreAlto||''; }catch(e){}
    try{ liberar(); }catch(e){}
  }

  var anclados=[];""", 'pantalla completa del marco')

cambia("""    if(bot-top<300) top=Math.max(0,-r.top);
      return {top:top, height:Math.max(220,bot-top)};""",
"""    if(bot-top<300) top=Math.max(0,-r.top);
      /* Con el marco a pantalla completa, la ventana entera es la banda:
         el marco esta por encima de la cabecera del sitio, asi que no hay
         nada que descontar. */
      if(pantalla) return {top:0, height:alturaSitio()};
      return {top:top, height:Math.max(220,bot-top)};""", 'banda en pantalla completa')

cambia("""    anclados.push(ov);
    medirCabecera();                  /* antes de anclar, no despues */""",
"""    anclados.push(ov);
    medirCabecera();                  /* antes de anclar, no despues */
    aPantallaCompleta();              /* si no, la ficha se recorta al marco */""",
       'pantalla completa al abrir')

cambia("""    if(!document.querySelector('.cpm-ov-live')){
      document.body.style.overflow='';
      destrabarSitio();
    }""",
"""    if(!document.querySelector('.cpm-ov-live')){
      document.body.style.overflow='';
      destrabarSitio();
      salirPantallaCompleta();
    }""", 'salir de pantalla completa al cerrar')

cambia("""      if(!anclados.length && scrollGuardado) destrabarSitio();""",
"""      if(!anclados.length && scrollGuardado) destrabarSitio();
      /* Misma red: un marco que se quedara fijo taparia el sitio entero. */
      if(!anclados.length && pantalla) salirPantallaCompleta();
      else if(pantalla){
        try{ FRAME.el.style.setProperty('height',alturaSitio()+'px','important'); }catch(e){}
      }""", 'red de seguridad de la pantalla completa')

# liberar() y bleed() no deben pelearse con el marco fijo.
cambia("""  function liberar(){
    var el=root.parentElement, n=0;""",
"""  function liberar(){
    /* Con el marco a pantalla completa no se toca nada: al cerrar se
       restaura el estilo guardado y se vuelve a llamar a esto. */
    if(pantalla) return;
    var el=root.parentElement, n=0;""", 'liberar en pantalla completa')

# ══════════════════════════════════════════════════════════════════════
# 17. CATEGORIA NUEVA, IMPERIO CON UBICACION, Y BOTON AL MAPA
# ══════════════════════════════════════════════════════════════════════
# a) La lista de categorias libres estaba escrita TRES veces: en las
#    pastillas, en las casillas del editor y -- literal -- dentro del
#    filtro. Anadir una y olvidarse de la tercera deja una pastilla que
#    no filtra nada. Ahora hay una sola lista y las tres salen de ella.
cambia("""  var CATS = ["Todos","Terrenos","Macrolotes","Playa","Casas","Departamentos","Ranchos y Haciendas","Exclusivos"];
  var CATEGORIAS_DISP = ["Playa","Casas","Departamentos","Ranchos y Haciendas","Exclusivos (no publicar)"];""",
"""  /* Categorias que se marcan a mano en cada propiedad. UNA sola lista:
     de aqui salen las pastillas de arriba, las casillas del editor y el
     filtro. Para anadir una categoria, se anade aqui y ya. */
  var CATS_LIBRES = ["Playa","Casas","Departamentos","Ranchos y Haciendas","Comerciales/Oficinas"];
  var CATS = ["Todos","Terrenos","Macrolotes"].concat(CATS_LIBRES).concat(["Exclusivos"]);
  var CATEGORIAS_DISP = CATS_LIBRES.concat(["Exclusivos (no publicar)"]);""",
       'lista unica de categorias')

cambia("""      if(['Playa','Casas','Departamentos','Ranchos y Haciendas'].indexOf(filtro)>=0){
        if(cats(t).indexOf(filtro)<0) return false;
      }""",
"""      if(CATS_LIBRES.indexOf(filtro)>=0){
        if(cats(t).indexOf(filtro)<0) return false;
      }""", 'filtro por la lista unica')

# b) Imperio Conkal no es un documento de Firestore, asi que no se puede
#    editar desde la pantalla: sus datos viven en el codigo. Aqui van sus
#    coordenadas.
cambia("""    ubicacion_maps:'https://maps.app.goo.gl/NyWBRxtysDm8GLP48',
    estado_propiedad:'disponible',""",
"""    ubicacion_maps:'https://maps.app.goo.gl/NyWBRxtysDm8GLP48',
    /* Del Plus Code 3F9W+27F Conkal, Yucatan. Esta ficha no vive en
       Firestore -- por eso no tiene boton de editar --, asi que su
       ubicacion se escribe aqui. La misma pareja esta en el guion del
       mapa (tools/mapa_js.txt): si se cambia una, cambiar la otra. */
    lat:21.067563,
    lng:-89.504328,
    estado_propiedad:'disponible',""", 'coordenadas de Imperio Conkal')

# c) Boton al mapa de propiedades, en pestaña nueva.
#    La direccion NO se escribe a mano: se busca en el menu real del
#    sitio, igual que hacen los bloques de la portada y de divisiones,
#    y solo si no aparece se usa la ruta de respaldo.
cambia("""  var CDN = {
    app:""",
"""  /* Pagina del mapa de la cartera. Primero se busca en el menu real del
     sitio por estos nombres; si no esta, se usa la ruta de respaldo. Esa
     ruta es lo unico que hay que tocar si la pagina cambia de sitio. */
  var CLAVES_MAPA = ["mapa de propiedades","mapa de la cartera","mapa de terrenos","ubicaciones","mapa"];
  var RUTA_MAPA = "/mapa-de-propiedades";

  var CDN = {
    app:""", 'configuracion del enlace al mapa')

cambia("""  /* Abre una direccion fuera del bloque.""",
"""  /* ─────────────────────────────────────────────────────────
     A DONDE ENLAZA EL BOTON DEL MAPA
     Se lee el menu del sitio y se enlaza donde enlaza la propia
     navegacion. Escribir la ruta a mano envejece mal: en cuanto la
     pagina cambia de direccion, el boton lleva a un 404.
     ───────────────────────────────────────────────────────── */
  function sinTildes(t){
    t=(t||'').toLowerCase();
    try{ t=t.normalize('NFD').replace(RE_DIACRITICOS,''); }catch(e){}
    return t.replace(/\s+/g,' ').trim();
  }
  var menuSitio=null;
  function leerMenu(){
    if(menuSitio) return menuSitio;
    menuSitio={};
    try{
      var doc=documentoSitio();
      var origen=doc.location && doc.location.origin;
      var anclas=doc.querySelectorAll('a[href]');
      for(var i=0;i<anclas.length;i++){
        var a=anclas[i], h=a.getAttribute('href')||'';
        if(/^(#|mailto:|tel:|javascript:)/i.test(h)) continue;
        var u; try{ u=new URL(h, doc.baseURI); }catch(e){ continue; }
        if(origen && u.origin!==origen) continue;
        if(!u.pathname.replace(/\/+$/,'')) continue;        /* la portada */
        var t=sinTildes(a.textContent);
        if(!t || t.length>40) continue;
        /* "Mapa del sitio" no es el mapa de la cartera. */
        if(/aviso|privacidad|terminos|cookies|politica|mapa del sitio/.test(t)) continue;
        if(!menuSitio[t]) menuSitio[t]=u.href;
      }
    }catch(e){}
    return menuSitio;
  }
  /* Coincidencia exacta primero, y luego por el principio del texto. Nada
     de buscar la palabra en cualquier posicion: asi es como se acaba
     enlazando a la pagina equivocada. */
  function rutaDelSitio(claves){
    var m=leerMenu(), i, t;
    for(i=0;i<claves.length;i++){ if(m[sinTildes(claves[i])]) return m[sinTildes(claves[i])]; }
    for(i=0;i<claves.length;i++){
      var k=sinTildes(claves[i]);
      for(t in m){ if(Object.prototype.hasOwnProperty.call(m,t) && t.indexOf(k)===0) return m[t]; }
    }
    return null;
  }
  function urlMapa(){
    var base='';
    try{ base=documentoSitio().location.origin||''; }catch(e){}
    return rutaDelSitio(CLAVES_MAPA) || (base+RUTA_MAPA);
  }

  /* Abre una direccion fuera del bloque.""", 'resolucion del enlace al mapa')

cambia("""        (admin?'<button class="cpm-mini" id="cpm-new">+ Nueva</button>':'')+
        '<span class="cpm-user">'""",
"""        (admin?'<button class="cpm-mini" id="cpm-new">+ Nueva</button>':'')+
        '<button class="cpm-mini" id="cpm-mapa" title="Ver la cartera sobre el mapa (se abre en otra pestaña)">🗺 Mapa</button>'+
        '<span class="cpm-user">'""", 'boton del mapa en la barra')

cambia("""    root.querySelector('#cpm-logout').addEventListener('click',function(){ firebase.auth().signOut(); });""",
"""    root.querySelector('#cpm-logout').addEventListener('click',function(){ firebase.auth().signOut(); });
    root.querySelector('#cpm-mapa').addEventListener('click',function(){ abrirFuera(urlMapa()); });""",
       'enlace del boton del mapa')

# ══════════════════════════════════════════════════════════════════════
# 11. VERIFICACION
# ══════════════════════════════════════════════════════════════════════
problemas = []
for i, js in enumerate(re.findall(r'<script>(.*?)</script>', src, re.S)):
    f = os.path.join(tempfile.gettempdir(), 'chk_port_%d.js' % i)
    open(f, 'w', encoding='utf-8').write(js)
    r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
    if r.returncode:
        problemas.append('JS invalido en el bloque %d: %s'
                         % (i, (r.stderr.split(chr(10)) + ['', '', ''])[2].strip()[:110]))
if src.count('<style>') != src.count('</style>'):
    problemas.append('<style> desparejado')
if src.count('<script') != src.count('</script>'):
    problemas.append('<script> desparejado')

# La ficha en PDF se arma como un documento COMPLETO dentro de una cadena
# de JavaScript y se abre en otra ventana: ahi <!doctype>, <html>, <style>
# y los selectores sin acotar son correctos. Se saca del texto antes de
# revisar, o cada revision la denunciaria.
ini_pdf = src.index('  function generarPDF(')
fin_pdf = src.index('imprimir(html, nombreArchivo, alSalir);', ini_pdf)
sin_pdf = src[:ini_pdf] + src[fin_pdf:]
if 'DOCTYPE' in sin_pdf:
    problemas.append('quedo un documento completo fuera de generarPDF')

limpio = re.sub(r'/\*.*?\*/', '', sin_pdf, flags=re.S)
limpio = re.sub(r'<!--.*?-->', '', limpio, flags=re.S)
for t in ['<!doctype', '<html', '<head', '<body']:
    if t in limpio.lower():
        problemas.append('contiene ' + t)

# El CSS, acotado al contenedor.
css = '\n'.join(re.findall(r'<style>(.*?)</style>', sin_pdf, re.S))
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
sueltos = []
for bloque in re.split(r'\}', css):
    if '{' not in bloque:
        continue
    sel = bloque.rsplit('{', 1)[0].strip()
    if not sel or sel.startswith('@') or sel.endswith(')'):
        continue
    for parte in sel.split(','):
        parte = parte.strip()
        if not parte or parte.startswith('@'):
            continue
        if not (parte.startswith('#cpm-portafolio') or parte.startswith('.cpm-ov')
                or parte.startswith('from') or parte.startswith('to')
                or parte.endswith('%')):
            sueltos.append(parte[:60])
if sueltos:
    problemas.append('%d selectores fuera del contenedor: %s'
                     % (len(sueltos), '; '.join(sorted(set(sueltos))[:5])))

# Que los cambios esten de verdad.
esperado = [
    ('correoNorm(user.email)', 'isAdmin sin distinguir mayusculas'),
    ('function esExclusiva', 'deteccion de exclusivas'),
    ('"lat","lng"', 'lat/lng en los campos publicos'),
    ('function olcDecodifica', 'decodificador de Plus Codes'),
    ('cpm-ed-coords', 'campo de coordenadas'),
    ('function openDiagnostico', 'panel de revision'),
    ('docsMalos.push', 'documentos ilegibles'),
    ('adoptadas++', 'adopcion de coordenadas del espejo'),
    ('class="excl"', 'sello de exclusiva en la tarjeta'),
    ('function medirCabecera', 'medida de la cabecera del sitio'),
    ('CABECERA-r.top', 'la banda descuenta la cabecera'),
    ('cpm-sheet-top', 'cabecera pegada de la hoja'),
    ('position:sticky', 'la cabecera de la hoja es pegada'),
    ('function imprimir', 'impresion con respaldos'),
    ('function verEnPantalla', 'ultimo recurso visible del PDF'),
    ('function alImprimir', 'espera a las fotos con tope'),
    ('function abrirFuera', 'apertura de enlaces fuera del marco'),
    ('ubi-txt', 'ubicacion escrita en el PDF'),
    ('function trabarSitio', 'traba del desplazamiento del sitio'),
    ("ev.key!=='Escape'", 'Escape cierra'),
    ('function aPantallaCompleta', 'marco a pantalla completa'),
    ('function salirPantallaCompleta', 'vuelta del marco a su sitio'),
    ('no se ancla a la ventana', 'comprobacion del anclaje'),
    ('Comerciales/Oficinas', 'categoria nueva'),
    ('var CATS_LIBRES', 'lista unica de categorias'),
    ('lat:21.067563', 'ubicacion de Imperio Conkal'),
    ('function urlMapa', 'enlace al mapa de propiedades'),
    ('id="cpm-mapa"', 'boton del mapa'),
    ('alto /= 5; ancho /= 4;', 'rejilla fina de los Plus Codes'),
    ("ev.key==='ArrowLeft'", 'flechas en la galeria'),
]
# Lo que NO debe quedar.
for aguja, que in [
    ('backdrop-filter', 'el desenfoque del velo, que cuesta fotogramas'),
    ('window.onload=function(){window.print()}', 'la impresion atada a onload'),
    ("top:calc(50% + 8px)", 'el centrado a mano de la lupa'),
]:
    if aguja in sin_comentarios(src):
        problemas.append('sigue presente: ' + que)
for aguja, que in esperado:
    if aguja not in src:
        problemas.append('falta: ' + que)

# Y que no quede ninguna comparacion literal con la categoria vieja.
for m in re.finditer(r"indexOf\('Exclusivos \(no publicar\)'\)", src):
    ctx = src[max(0, m.start() - 90):m.start()]
    if 'CATEGORIAS_DISP' not in ctx:
        problemas.append('queda una comparacion literal con la categoria vieja')
        break

print('  isAdmin insensible a mayusculas :', 'correoNorm(user.email)' in src)
print('  exclusivas visibles al asesor   :', 'function visibles(){ return terrenos.slice(); }' in src)
print('  campo de coordenadas            :', src.count('cpm-ed-coords'))
print('  tablas compartidas con el mapa  :', src.count('var LOCALIDADES'), src.count('var CENTRO_ESTADO'))
print('  problemas                       :', problemas or 'ninguno')
if problemas:
    sys.exit(1)
open(DESTINO, 'w', encoding='utf-8').write(src)
print('  escrito                         :', round(len(src) / 1024), 'KB ->',
      os.path.relpath(DESTINO, RAIZ))
