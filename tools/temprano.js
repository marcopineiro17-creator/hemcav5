<script>
/* Se ejecuta antes de que el navegador pinte el bloque.
   Fija --vh-real con la altura de la ventana REAL (la del documento padre si
   estamos dentro de un iframe) y pinta el fondo del documento.
   Es imprescindible hacerlo aqui: si el CSS llega a evaluar 100svh contra el
   viewport del iframe (que puede medir miles de pixeles), el hero y las etapas
   nacen gigantes, el anfitrion dimensiona el iframe con ese valor inflado y
   queda la franja blanca al final. */
(function () {
  var d = document.currentScript, r = d && d.parentNode;
  if (!r) return;
  var H = 0;
  try { H = (window.self !== window.top && window.parent.innerHeight) || window.innerHeight; }
  catch (e) { H = window.innerHeight; }
  if (H > 0) { try { r.style.setProperty('--vh-real', H + 'px'); } catch (e) {} }
  try {
    if (window.self !== window.top) {
      var c = getComputedStyle(r).backgroundColor;
      if (c && c !== 'transparent' && c !== 'rgba(0, 0, 0, 0)') {
        document.documentElement.style.background = c;
      }
    }
  } catch (e) {}
})();
</script>