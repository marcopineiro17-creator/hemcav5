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
    /* Y avisamos, por si el anfitrion prefiere gestionarlo el. */
    try { window.parent.postMessage({ type: "hb:height", height: alto }, "*"); } catch (e) {}
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
    requestAnimationFrame(function () { ajustePedido = false; ajustarMarco(); });
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
  /* Posicion del elemento en el viewport REAL. */
  function techo(el, S) {
    try { return el.getBoundingClientRect().top + S; } catch (e) { return 0; }
  }
  function limita(v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }

  /* ---------- registros ---------- */
  var entradas = [], continuos = [], encolado = false, sondeo = null;

  function alEntrar(el, cb) { if (el) entradas.push({ el: el, cb: cb }); }
  function continuo(fn) { if (fn) continuos.push(fn); }

  function ciclo() {
    encolado = false;
    /* Aqui NO se toca la altura del iframe. Hacerlo en cada fotograma
       obligaba al padre a recalcular, lo que movia el iframe, lo que
       cambiaba todas las medidas, lo que generaba un transform distinto...
       Ese bucle era la vibracion y el arrastre de los elementos anclados.
       La altura se ajusta aparte, solo cuando el contenido cambia. */
    sincronizarVista();
    var H = altoVista(), S = desfaseMarco();

    for (var i = entradas.length - 1; i >= 0; i--) {
      var it = entradas[i];
      if (techo(it.el, S) < H * 0.93) {
        it.el.classList.add(opts.claseVisible || "in");
        if (it.cb) { try { it.cb(it.el); } catch (e) {} }
        entradas.splice(i, 1);
      }
    }
    if (!entradas.length && sondeo) { clearInterval(sondeo); sondeo = null; }

    for (var j = 0; j < continuos.length; j++) {
      try { continuos[j](H, S); } catch (e) {}
    }
  }
  function pedir() { if (!encolado) { encolado = true; requestAnimationFrame(ciclo); } }

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
    limita: limita,
    enMarco: enMarco,
    legible: legible,
    lento: lento
  };
}
