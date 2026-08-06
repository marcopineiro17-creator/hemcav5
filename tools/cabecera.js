<script>
/* Primera linea del bloque: fija --vh-real en la raiz del documento antes de
   que el CSS se aplique a nada. Las propiedades personalizadas se heredan, asi
   que el valor llega a todo el bloque. Sin esto, 100svh se evaluaria una vez
   contra el viewport del iframe -- que puede medir miles de pixeles -- y el
   anfitrion dimensionaria el iframe con ese valor inflado: de ahi la franja
   blanca interminable al final. */
(function () {
  var H = 0;
  try { H = (window.self !== window.top && window.parent.innerHeight) || window.innerHeight; }
  catch (e) { H = window.innerHeight; }
  if (H > 0) try { document.documentElement.style.setProperty('--vh-real', H + 'px'); } catch (e) {}
  /* Solo se reajusta ante cambios grandes (girar el telefono). Los pequenos
     -- la barra de direcciones al desplazarse -- se ignoran a proposito: si
     este valor se mueve, cambian las alturas, el anfitrion redimensiona el
     iframe y aparece el temblor. */
  function s() {
    var h = 0;
    try { h = (window.self !== window.top && window.parent.innerHeight) || window.innerHeight; }
    catch (e) { h = window.innerHeight; }
    if (h > 0 && Math.abs(h - H) > 80) {
      H = h;
      try { document.documentElement.style.setProperty('--vh-real', h + 'px'); } catch (e) {}
    }
  }
  window.addEventListener('resize', s, { passive: true });
  try { if (window.self !== window.top) window.parent.addEventListener('resize', s, { passive: true }); } catch (e) {}
})();
</script>