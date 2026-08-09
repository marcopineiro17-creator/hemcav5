/* ===================================================================
   MOTOR DE SCROLL PARA BLOQUES INCRUSTADOS  (compartido)
   -------------------------------------------------------------------
   EL PROBLEMA QUE RESUELVE
   Hostinger inserta el codigo personalizado dentro de un <iframe>. Si
   ese iframe mide menos que su contenido, se convierte en una ventana
   pequena sobre una pagina muy alta:
     - El iframe no hace scroll por dentro; el que se desplaza es el
       documento padre.
     - IntersectionObserver mide contra el viewport DEL IFRAME, asi que
       todo lo que quede por debajo de su caja nunca "entra a vista".
     - getBoundingClientRect() dentro del iframe no sabe donde esta el
       iframe en la pagina real.
   Resultado: el fondo se pinta (es CSS) pero el contenido se queda en
   opacity:0 -> "bajo y solo se carga el fondo".

   LA CURA, EN ORDEN
   1. Si el iframe es del mismo origen, se le fija la altura de su
      propio contenido. Asi desaparece el scroll interno y la geometria
      vuelve a ser coherente. Tambien se avisa por postMessage para los
      anfitriones que sepan escucharlo.
   2. El viewport de referencia es el del padre, y a cada medida se le
      suma el desplazamiento del iframe dentro de esa pagina.
   3. Se escucha el scroll del padre ademas del propio.
   4. Sondeo periodico por si no llega ningun evento.
   5. Red de seguridad: pasado un tiempo, lo que siga pendiente se
      muestra. Nunca puede quedar contenido invisible.
   6. Si el padre no es legible (otro origen), no se oculta nada: se
      renuncia a las animaciones de scroll antes que arriesgar una
      pagina en blanco.

   NUNCA escribe la posicion de scroll de nadie: eso es lo que hacia
   saltar la pagina al inicio.
   =================================================================== */
function hbEngine(root, opts) {
  "use strict";
  opts = opts || {};

  var lento = false;
  try { lento = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); } catch (e) {}

  /* ---------- contexto ---------- */
  var enMarco = false, padre = null, marco = null;
  try { enMarco = (window.self !== window.top); } catch (e) { enMarco = true; }
  if (enMarco) {
    try {
      marco = window.frameElement;
      if (marco && typeof window.parent.innerHeight === "number") padre = window.parent;
      if (!padre) marco = null;
    } catch (e) { marco = null; padre = null; }
  }
  /* Legible = podemos medir de verdad. Es la condicion para animar. */
  var legible = !enMarco || !!marco;

  /* Marca el contenedor cuando vive dentro de un iframe. El CSS la usa para
     ocultar el boton propio de WhatsApp: dentro del iframe no puede flotar
     (el iframe mide lo que su contenido), y el runtime global crea el real
     fuera. Se aplica aqui, que es donde se conoce el contexto. */
  if (enMarco) { try { root.classList.add("hb-en-marco"); } catch (e) {} }

  /* ---------- alto del viewport REAL como variable CSS ----------
     Al fijar la altura del iframe a la de su contenido, el viewport del
     iframe PASA A SER esa altura: 100svh dejaria de valer una pantalla y
     se realimentaria (mas alto -> mas contenido -> mas alto). Por eso las
     alturas de pantalla se toman de --vh-real, en pixeles, medidos sobre
     la pagina padre. El valor por omision en CSS es 100svh, para que
     funcione sin JS y fuera de un iframe. */
  var ultimaVista = 0;
  function sincronizarVista() {
    var H = altoVista();
    /* Holgura grande a proposito. Este valor alimenta las alturas del bloque:
       si se mueve, cambia el alto del contenido, el anfitrion redimensiona su
       iframe y la geometria se desplaza. Ese ida y vuelta es el temblor. En
       movil la barra de direcciones hace variar el viewport constantemente,
       asi que solo se atiende un cambio de orientacion o similar. */
    if (Math.abs(H - ultimaVista) < 80) return;
    ultimaVista = H;
    invalidarGeo();
    try { root.style.setProperty("--vh-real", H + "px"); } catch (e) {}
  }

  /* ---------- aviso de altura al anfitrion ---------- */
  var TECHO = 60000;
  var ultimaAltura = 0, subidas = 0, congelado = false;
  function ajustarMarco() {
    if (!enMarco || congelado) return;
    var alto = Math.ceil(root.getBoundingClientRect().height);
    /* Holgura de 6px: evita reajustes por diferencias de redondeo. */
    if (!alto || Math.abs(alto - ultimaAltura) < 6) return;

    if (alto > ultimaAltura + 8) { subidas++; } else { subidas = 0; }
    if (alto > TECHO || subidas > 12) {
      congelado = true;
      try {
        if (window.console && console.warn) {
          console.warn('[hbEngine] altura desbocada (' + alto + 'px): se congela. ' +
                       'Suele venir de una medida en vh/svh dentro del iframe; usa --vh-real.');
        }
      } catch (e) {}
      return;
    }
    ultimaAltura = alto;
    /* NO se escribe la altura del iframe.
       El constructor tambien la gestiona; si los dos escribimos el mismo
       valor entramos en una pugna: el iframe oscila entre dos alturas (eso
       se ve como vibracion) y puede quedarse en un valor mayor que el
       contenido (eso se ve como una franja blanca interminable al final).
       Aqui solo se AVISA de la altura; quien decide es el anfitrion.
       Para que el contenido no quede recortado, lo que si es nuestro es
       --vh-real: se fija antes del primer pintado (ver el guion que
       acompana al bloque), asi ninguna medida en svh se evalua nunca
       contra el viewport del iframe. */
    /* Se avisa con el tipo que el codigo global de CPM SI escucha.
       Su runtime reconoce "hummingbird:height" y al recibirlo llama a
       resizeFrame, que ademas colapsa la altura reservada del bloque de
       Hostinger (cleanContainer sobre grid-embed, layout-element,
       block-layout y section). Eso es lo que elimina la franja blanca.
       Antes se emitia "hb:height", un tipo que nadie atendia.
       Cada bloque puede pedir su propio tipo: el de divisiones usa
       "cpm-divisiones:height", que el runtime atiende sin crear ademas el
       boton flotante de WhatsApp. */
    var aviso = { type: opts.tipoAltura || "hummingbird:height", height: alto };
    if (opts.whatsapp) aviso.whatsappUrl = opts.whatsapp;
    if (opts.proyecto) aviso.project = opts.proyecto;
    try { window.parent.postMessage(aviso, "*"); } catch (e) {}
  }

  /* El documento del iframe es blanco por omision. Si el iframe queda un
     poco mas alto que el contenido, ese blanco asoma como una franja (o un
     fondo interminable al final). Se le pinta el mismo color del bloque. */
  function pintarFondo() {
    if (!enMarco) return;
    var color = "";
    try { color = getComputedStyle(root).backgroundColor; } catch (e) {}
    if (!color || color === "transparent" || color === "rgba(0, 0, 0, 0)") return;
    try {
      document.documentElement.style.background = color;
      if (document.body) document.body.style.background = color;
    } catch (e) {}
  }

  /* Agrupa las peticiones de ajuste: nunca mas de una por fotograma. */
  var ajustePedido = false;
  function programarAjuste() {
    if (ajustePedido) return;
    ajustePedido = true;
    requestAnimationFrame(function () { ajustePedido = false; invalidarGeo(); ajustarMarco(); });
  }

  /* ---------- geometria real ---------- */
  function altoVista() {
    if (padre) { try { return padre.innerHeight || window.innerHeight || 800; } catch (e) {} }
    return window.innerHeight || 800;
  }
  function desfaseMarco() {
    if (!marco) return 0;
    try { return marco.getBoundingClientRect().top; } catch (e) { return 0; }
  }
  /* ---------- geometria cacheada ----------
     Medido: con el motor parado, cero fotogramas perdidos; con el motor en
     marcha, veintitantos. El coste no estaba en pintar sino en MEDIR. Cada
     fotograma habia unas veinticinco llamadas a getBoundingClientRect, y como
     el fotograma anterior habia escrito estilos, la primera lectura obliga a
     recalcular estilo y maquetacion de un documento de 15000px. Eso es lo que
     se sentia como arrastre.

     La cura se apoya en una propiedad del sitio: al fijarle al iframe la
     altura de su contenido, el documento del iframe NO hace scroll. Su
     scroll siempre vale cero, asi que la posicion que devuelve
     getBoundingClientRect DENTRO del iframe es constante: no depende de por
     donde vaya el visitante. Se puede medir una vez y reutilizar.
     La posicion en la pantalla real es esa medida fija mas el desplazamiento
     del iframe, que se lee del documento PADRE. Dentro del iframe no queda
     ninguna lectura por fotograma, y sin lecturas no hay maquetacion forzada:
     eso es lo que devuelve los fotogramas, no ahorrar llamadas.

     Se mide con offsetTop en vez de getBoundingClientRect a proposito:
     getBoundingClientRect incluye los transform, y las entradas animan
     translateY. Una medida tomada a mitad de la animacion quedaria desviada.
     offsetTop no ve los transform, asi que el valor cacheado es el bueno
     desde el primer momento.

     Fuera de un iframe la posicion si cambia con el scroll, asi que ahi se
     lee en vivo: no hay iframe que dimensionar y el coste no es problema. */
  var geo = new WeakMap(), sello = 0;
  function invalidarGeo() { sello++; }
  function cajaDe(el) {
    var c = geo.get(el);
    if (c && c.s === sello) return c;
    var t = 0, h = 0;
    try {
      var n = el;
      while (n && n !== root && n.offsetParent) { t += n.offsetTop; n = n.offsetParent; }
      /* Y del contenedor a la ventana del iframe. Es constante mientras la
         maquetacion no cambie, asi que tambien se cachea. */
      t += techoDelBloque();
      h = el.offsetHeight;
    } catch (e) {}
    c = { s: sello, t: t, h: h };
    geo.set(el, c);
    return c;
  }
  var selloRaiz = -1, topRaiz = 0;
  function techoDelBloque() {
    if (selloRaiz === sello) return topRaiz;
    selloRaiz = sello;
    try { topRaiz = root.getBoundingClientRect().top; } catch (e) { topRaiz = 0; }
    return topRaiz;
  }
  /* Posicion del elemento en el viewport REAL. */
  function techo(el, S) {
    if (!marco) { try { return el.getBoundingClientRect().top + S; } catch (e) { return 0; } }
    return cajaDe(el).t + S;
  }
  /* Alto del elemento, de la misma medida cacheada. */
  function alto(el) {
    if (!marco) { try { return el.getBoundingClientRect().height; } catch (e) { return 0; } }
    return cajaDe(el).h;
  }
  function limita(v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }

  /* ---------- registros ---------- */
  var entradas = [], continuos = [], sondeo = null;

  function alEntrar(el, cb) { if (el) entradas.push({ el: el, cb: cb }); }
  function continuo(fn) { if (fn) continuos.push(fn); }

  /* ---------- marca de "esto se esta moviendo" ----------
     Los paneles de cristal usan backdrop-filter: blur(). Ese desenfoque hay
     que recalcularlo en cada fotograma en que cambia lo que hay detras, y
     mientras la pagina se desplaza cambia siempre. Medido, un radio de 12px
     cuesta unos 3 fotogramas perdidos por segundo y medio de scroll; con 4px
     el coste practicamente desaparece.
     De ahi esta marca: mientras hay movimiento el CSS reduce el radio (no lo
     quita: el texto de las tarjetas tiene que seguir legible sobre las
     capturas), y al detenerse vuelve el desenfoque completo. En movimiento la
     diferencia no se aprecia; quieto, que es cuando se mira, esta intacto. */
  var refPrevia = null, moviendo = false, quietoDesde = 0;
  function marcaMovimiento(si) {
    if (si === moviendo) return;
    moviendo = si;
    try { root.classList[si ? "add" : "remove"]("hb-moviendo"); } catch (e) {}
  }
  /* Solo se encarga de QUITAR la marca: ponerla se hace en pedir(), que corre
     de forma sincrona en el propio evento de scroll. Si se pusiera aqui,
     dentro del requestAnimationFrame, el primer fotograma de cada gesto ya
     habria pagado el desenfoque caro -- y el principio del gesto es
     justamente donde mas se nota el tiron. */
  function vigilarMovimiento(S) {
    var ref = marco ? S : (window.pageYOffset || 0);
    var salto = refPrevia === null ? 0 : Math.abs(ref - refPrevia);
    refPrevia = ref;
    if (salto > 1) { quietoDesde = 0; marcaMovimiento(true); return; }
    if (!moviendo) return;
    if (!quietoDesde) quietoDesde = Date.now();
    else if (Date.now() - quietoDesde > 140) { quietoDesde = 0; marcaMovimiento(false); }
  }

  function ciclo() {
    /* Aqui NO se toca la altura del iframe. Hacerlo en cada fotograma
       obligaba al padre a recalcular, lo que movia el iframe, lo que
       cambiaba todas las medidas, lo que generaba un transform distinto...
       Ese bucle era la vibracion y el arrastre de los elementos anclados.
       La altura se ajusta aparte, solo cuando el contenido cambia. */
    sincronizarVista();
    var H = altoVista(), S = desfaseMarco();
    vigilarMovimiento(S);

    for (var i = entradas.length - 1; i >= 0; i--) {
      var it = entradas[i];
      if (techo(it.el, S) < H * 0.93) {
        it.el.classList.add(opts.claseVisible || "in");
        if (it.cb) { try { it.cb(it.el); } catch (e) {} }
        entradas.splice(i, 1);
      }
    }
    if (!entradas.length && sondeo) { clearInterval(sondeo); sondeo = null; }

    /* Primero se LEE todo, luego se ESCRIBE todo.
       Si cada funcion lee getBoundingClientRect y escribe estilos acto
       seguido, el navegador se ve obligado a recalcular la maquetacion en
       cada paso: con veinte funciones son veinte recalculos por fotograma.
       Eso es lo que se ve como temblor. Aqui las escrituras se acumulan y
       se aplican juntas al final, con una sola maquetacion. */
    for (var j = 0; j < continuos.length; j++) {
      try { continuos[j](H, S); } catch (e) {}
    }
    for (var w = 0; w < cola.length; w += 3) {
      try {
        if (cola[w + 1] === "@prop") cola[w].style.setProperty(cola[w + 2][0], cola[w + 2][1]);
        else cola[w].style[cola[w + 1]] = cola[w + 2];
      } catch (e) {}
    }
    cola.length = 0;
  }

  /* Encola una escritura de estilo. Salta las que no cambian nada: evita
     invalidaciones inutiles, que tambien encarecen cada fotograma. */
  var cola = [], previo = new WeakMap();
  function escribe(el, prop, valor) {
    if (!el) return;
    var m = previo.get(el);
    if (!m) { m = {}; previo.set(el, m); }
    if (m[prop] === valor) return;
    m[prop] = valor;
    cola.push(el, prop, valor);
  }
  function escribeProp(el, nombre, valor) {
    if (!el) return;
    var m = previo.get(el);
    if (!m) { m = {}; previo.set(el, m); }
    if (m[nombre] === valor) return;
    m[nombre] = valor;
    cola.push(el, "@prop", [nombre, valor]);
  }
  /* Bucle vivo mientras se desplaza.
     Antes se encolaba un requestAnimationFrame por cada evento de scroll,
     pero el navegador agrupa esos eventos: el fotograma se calculaba con una
     posicion ya vieja y el elemento anclado iba siempre un paso por detras.
     Eso es lo que se percibe como temblor. Aqui, en cuanto hay scroll, el
     bucle se encadena solo y recalcula en CADA fotograma con la posicion
     fresca; se apaga tras un momento de quietud para no gastar de mas. */
  var vivo = false, hastaQuietud = 0;
  function late() {
    ciclo();
    if (Date.now() < hastaQuietud) { requestAnimationFrame(late); }
    else { vivo = false; }
  }
  function pedir() {
    hastaQuietud = Date.now() + 420;
    /* Aqui, no en el bucle: esto corre en el mismo evento de scroll, antes de
       que el navegador pinte, asi que el desenfoque barato ya rige en el
       primer fotograma del gesto. */
    quietoDesde = 0;
    marcaMovimiento(true);
    if (!vivo) { vivo = true; requestAnimationFrame(late); }
  }

  /* ---------- mostrar todo (red de seguridad y modo sin medida) ---------- */
  function mostrarTodo() {
    for (var i = 0; i < entradas.length; i++) {
      entradas[i].el.classList.add(opts.claseVisible || "in");
      if (entradas[i].cb) { try { entradas[i].cb(entradas[i].el); } catch (e) {} }
    }
    entradas.length = 0;
    if (sondeo) { clearInterval(sondeo); sondeo = null; }
  }

  /* ---------- arranque ---------- */
  function arrancar() {
    sincronizarVista();
    pintarFondo();
    ajustarMarco();

    /* Saludo al runtime global: al recibir "hummingbird:ready" crea el boton
       flotante de WhatsApp FUERA del iframe (dentro no puede ser flotante de
       verdad) y pide la altura. */
    if (enMarco) {
      /* El saludo hace que el runtime global cree el boton flotante de
         WhatsApp. Solo lo mandan los bloques que lo quieren. */
      if (opts.whatsapp) {
        try {
          window.parent.postMessage({ type: "hummingbird:ready",
                                      whatsappUrl: opts.whatsapp }, "*");
        } catch (e) {}
      }
      window.addEventListener("message", function (ev) {
        var d = ev && ev.data;
        if (d && (d.type === "hummingbird:request-height" || d.type === "cpm-divisiones:request-height")) {
          ultimaAltura = 0;      /* fuerza el reenvio */
          programarAjuste();
        }
      });
      [300, 900, 2000].forEach(function (ms) {
        setTimeout(function () { ultimaAltura = 0; programarAjuste(); }, ms);
      });
    }

    /* Sin medida fiable o sin movimiento: todo visible, cero scroll. */
    if (!legible || lento) {
      mostrarTodo();
      continuos.length = 0;
      if (opts.alRendirse) { try { opts.alRendirse(); } catch (e) {} }
      seguirAltura();
      diagnostico();
      return;
    }

    function liga(w) {
      try {
        w.addEventListener("scroll", pedir, { passive: true });
        w.addEventListener("resize", pedir, { passive: true });
      } catch (e) {}
    }
    liga(window);
    if (padre) liga(padre);

    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) { ciclo(); pedir(); }
    });

    /* Sondeo: cubre el caso de que no llegue ningun evento de scroll.
       Llama a ciclo() directo porque requestAnimationFrame se congela
       en pestanas de segundo plano. */
    sondeo = setInterval(ciclo, 300);

    pedir();
    [80, 300, 800, 1600, 3000].forEach(function (ms) { setTimeout(pedir, ms); });
    window.addEventListener("load", pedir);
    try { if (document.fonts && document.fonts.ready) document.fonts.ready.then(pedir); } catch (e) {}
    seguirAltura();

    /* Red de seguridad final: nada se queda invisible. */
    setTimeout(mostrarTodo, opts.limite || 9000);
    diagnostico();
  }

  /* La altura cambia con fuentes e imagenes: hay que reajustar el marco. */
  function seguirAltura() {
    if (!enMarco) return;
    try { new ResizeObserver(programarAjuste).observe(root); } catch (e) {}
    window.addEventListener("load", function () { programarAjuste(); pintarFondo(); });
    window.addEventListener("resize", function () { sincronizarVista(); programarAjuste(); });
    if (padre) { try { padre.addEventListener("resize", function () { sincronizarVista(); programarAjuste(); }, { passive: true }); } catch (e) {} }
    [400, 1200, 2500].forEach(function (ms) { setTimeout(programarAjuste, ms); });
    Array.prototype.slice.call(root.querySelectorAll("img")).forEach(function (im) {
      if (!im.complete) im.addEventListener("load", function () { programarAjuste(); pedir(); }, { once: true });
    });
  }

  /* Diagnostico. Anadir ?hbdebug=1 a la URL publicada muestra un recuadro
     con lo que el motor esta midiendo de verdad. Es la forma rapida de
     saber que hace el bloque dentro del Hostinger real. */
  /* Diagnostico. Anadir ?hbdebug=1 a la URL publicada muestra un recuadro
     con lo que el motor esta midiendo de verdad. Es la forma rapida de saber
     que hace el bloque dentro del Hostinger real. */
  function diagnostico() {
    var on = false;
    try { on = /[?&]hbdebug=1/.test(location.search); } catch (e) {}
    if (!on) { try { on = /[?&]hbdebug=1/.test(padre.location.search); } catch (e) {} }
    if (!on || !document.body) return;
    var caja = document.createElement('div');
    caja.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:99999;max-width:340px;' +
      'padding:10px 12px;background:#0b0b14;color:#9ecfff;border:1px solid #4466ff;' +
      'border-radius:9px;font:11px/1.5 monospace;white-space:pre-wrap;pointer-events:none';
    document.body.appendChild(caja);
    setInterval(function () {
      var am = 0, ac = Math.round(root.getBoundingClientRect().height);
      try { am = marco ? Math.round(marco.getBoundingClientRect().height) : 0; } catch (e) {}
      var lineas = [
        'motor hb',
        'en iframe: ' + enMarco + (enMarco ? (marco ? ' (padre legible)' : ' (padre NO legible)') : ''),
        'viewport real: ' + Math.round(altoVista()) + 'px',
        'desfase del iframe: ' + Math.round(desfaseMarco()) + 'px',
        'alto del contenido: ' + ac + 'px',
        'alto del iframe: ' + am + 'px' + (am && Math.abs(am - ac) > 40 ? '  << DESAJUSTE' : ''),
        'pendientes: ' + entradas.length + '   continuos: ' + continuos.length
      ];
      caja.textContent = lineas.join(String.fromCharCode(10));
    }, 500);
  }

  return {
    diagnostico: diagnostico,
    escribe: escribe,
    escribeProp: escribeProp,
    alEntrar: alEntrar,
    continuo: continuo,
    pedir: pedir,
    arrancar: arrancar,
    mostrarTodo: mostrarTodo,
    altoVista: altoVista,
    sincronizarVista: sincronizarVista,
    programarAjuste: programarAjuste,
    desfase: desfaseMarco,
    techo: techo,
    alto: alto,
    invalidarGeo: invalidarGeo,
    limita: limita,
    enMarco: enMarco,
    legible: legible,
    lento: lento
  };
}
