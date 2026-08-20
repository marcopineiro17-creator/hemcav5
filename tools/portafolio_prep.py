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
    var latBaja = -90, lngBaja = -180, res = 20, celda = 20;
    for(var k=0;k+1<c.length && k<10;k+=2){
      var ia = OLC_A.indexOf(c.charAt(k)), ib = OLC_A.indexOf(c.charAt(k+1));
      if(ia < 0 || ib < 0) return null;
      latBaja += ia*res; lngBaja += ib*res;
      celda = res; res /= 20;
    }
    return {lat:latBaja + celda/2, lng:lngBaja + celda/2, celda:celda};
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
fin_pdf = src.index('w.document.write(html); w.document.close();', ini_pdf)
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
]
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
