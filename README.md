# HEMCA — sitio web (una sola página)

Sitio estático, sin dependencias ni build. Sólo dos cosas:

```
index.html      ← la página completa (HTML + CSS + JS en un archivo)
assets/         ← 14 imágenes y logotipos + favicon
```

## Cómo subirlo a Hostinger

Usa **hPanel → Administrador de archivos** (no el editor de "insertar código"):

1. Entra a hPanel → *Sitio web* → **Administrador de archivos**.
2. Abre la carpeta **`public_html`** y borra lo que haya dentro
   (por ejemplo el `default.php` o `index.html` de bienvenida).
3. Sube **`index.html`** y la carpeta **`assets`** completa,
   una al lado de la otra, dentro de `public_html`.
4. Listo. La estructura final debe verse así:

```
public_html/
├── index.html
└── assets/
    ├── hero-obra.jpg
    ├── etapa-analizar.jpg
    └── ... (el resto de imágenes)
```

> **Importante:** `index.html` y `assets/` deben quedar en el **mismo nivel**.
> Si `assets/` se sube dentro de otra carpeta, las imágenes no cargan.

### Lo que NO hay que hacer

- **No** pegar este archivo en un bloque de "código personalizado" o "embed"
  del constructor de webs. Es un documento HTML completo (`<!doctype html>`,
  `<head>`, `<body>`): dentro de otra página rompe el diseño del constructor.
  Va subido como archivo, según los pasos de arriba.
- **No** renombrar los archivos de `assets/`. Las rutas están escritas en
  `index.html`; si cambia un nombre, hay que cambiarlo también ahí.

## Bloques para el contenedor de código de Hostinger

Además de la página suelta de HEMCA, hay seis bloques pensados para pegarse
en un contenedor de código del constructor. No llevan etiquetas de documento,
todo su CSS está acotado a su propio contenedor y no dependen de ningún CDN
de scripts.

| Archivo | Va en | Contenedor |
| --- | --- | --- |
| `hemca-embed-hostinger.html` | la página de HEMCA | `.hemca` |
| `portafolio-hms-embed.html` | el portafolio de Hummingbird | `#hbp` |
| `divisiones-embed-hostinger.html` | `/divisiones` | `#cpm-divisiones` |
| `inicio-embed-hostinger.html` | la portada | `#cpm-home` |
| `catalogo-embed-hostinger.html` | `/catalogo-de-propiedades` | `#cpm-catalogo` |
| `predios-embed-hostinger.html` | `/regularizacion-predios` | `#cpm-predios` |

Se construyen con `tools/` (`css_prep.py`, `div_prep.py`, `home_prep.py`,
`cat_prep.py`, `predios.py`, `build.py`); no se editan a mano, porque el guion vuelve a generarlos desde el
original. Los originales de partida están en `src/`.

### Regularización de Predios

Es el único bloque que no parte de un original pegado: se escribe aquí, en
tres piezas —`tools/predios_css.txt`, `predios_html.txt` y `predios_js.txt`—
que `tools/predios.py` une con el motor y revisa antes de publicar.

Marca propia, distinta de HEMCA y de HMS: fondo blanco, tipografía con serif
del sistema para los títulos (formal, y sin depender de un CDN de fuentes) y
como secundario el azul `#051958`, que es el que ya identifica a la división
legal en el bloque de Divisiones. No se inventó un color nuevo.

**Lo que hay que editar a mano** son dos cosas, las dos al principio del guion:

- `WHATSAPP`. Se dejó vacía a propósito: los dos números que hay en el sitio
  son de HEMCA y de HMS, y mandar ahí a alguien que quiere escriturar sería
  peor que no tener botón. Mientras esté vacía, los botones de WhatsApp llevan
  a la página de contacto y el bloque funciona igual.
- `FOTOS`. Cinco huecos —`portada`, `escritura`, `hipoteca`, `alcance` y
  `cierre`— donde va la dirección de cada imagen; las de Hostinger sirven tal
  cual. **Un hueco vacío no se ve vacío:** debajo hay una ilustración
  vectorial —el plano de subdivisión que se dibuja solo, la escritura con su
  sello, el gravamen cancelándose— hecha para sostenerse sola, y la foto sólo
  la sustituye cuando existe. Así la página se puede publicar hoy e ir
  poniendo fotos después. Cuando hay foto, se le aplica un velo azul para que
  el texto se lea venga la imagen que venga.

Del movimiento: los trazos de los planos se dibujan con `stroke-dashoffset`,
los sellos caen y se asientan, la línea del proceso se llena según avanzas
—medida contra el recorrido de la sección por la pantalla, no contra su
distancia al borde, que llenaba la barra de golpe— y las fotos llevan un
paralaje corto. Nada de `backdrop-filter` ni de rotaciones sobre superficies
grandes: medido en la réplica, 58 fps y 5 fotogramas lentos de 138.

Un detalle de SVG que costó encontrar: un grupo que se posiciona con el
atributo `transform` y además se anima por CSS **pierde la posición**, porque
la propiedad CSS sustituye al atributo entero y la pieza salta al origen. Por
eso cada sello y cada pieza animada va envuelta: el grupo de fuera coloca, el
de dentro anima.

Este bloque **escribe él mismo la altura del iframe** (`escribeAltura` en el
motor), al revés que los demás. El motor evita hacerlo porque el runtime
global de CPM también la escribe y las dos manos sobre el mismo valor
producían la vibración; pero ese runtime sólo reconoce `#hb-lp`, `#ic-lp` y
`#cpm-divisiones`, así que a `#cpm-predios` no le contesta nadie: sin escribirla,
el iframe se queda en 150 px sobre un contenido de 7 000. Como aquí no hay dos
escritores, no hay pugna posible.

### Destinos de los enlaces

Los bloques de **Divisiones** y de la **portada** enlazan al resto del sitio.
Para no depender de rutas escritas a mano —que se quedan viejas en cuanto una
página cambia de sitio— **buscan cada destino en el menú real del sitio** y
enlazan donde enlaza tu propia navegación; sólo si no lo encuentran usan una
ruta de respaldo. Todos abren en la ventana completa (`target="_top"`), no
dentro del iframe.

Las tablas de respaldo son el único sitio que hay que tocar si una dirección
cambia: `DESTINOS` en `tools/build.py` (divisiones) y en `tools/home_prep.py`
(portada).

Portada:

| Tarjeta | Se busca en el menú como | Respaldo |
| --- | --- | --- |
| Venta y promoción inmobiliaria | servicios inmobiliarios / inmobiliaria | `/servicios-inmobiliarios` |
| Servicios legales | legal / división legal / jurídico | `/division-legal` |
| Marketing inmobiliario y empresarial | hms / hummingbird | `/hms` |
| Construcción y remodelación | hemca | `/hemca` |
| Desarrollo, ejecución y venta | servicios inmobiliarios / inmobiliaria | `/servicios-inmobiliarios` |
| Avalúo y escrituración | regularización / regularización de predios | `/regularizacion-predios` |

Las claves de HEMCA y HMS son a propósito estrechas: si incluyeran
«construcción» o «marketing», el menú podría devolver esas otras páginas y el
enlace acabaría donde no se pidió.

Las dos tarjetas que van a servicios inmobiliarios apuntan además **al
apartado que les corresponde**. Como los identificadores de esa página no se
pueden saber de antemano, se miran cuando hacen falta: al pasar el puntero por
la tarjeta se pide la página una vez, se busca el título que corresponde y se
añade su ancla. Si falla algo, el enlace se queda apuntando a la página.

### El catálogo y la altura reservada por Hostinger

El constructor mide el bloque una vez y guarda esa altura en los contenedores
del iframe: alto fijo en `.grid-embed`, `min-height` en la sección y —el que de
verdad manda— una **fila de rejilla de alto fijo** en `.block-layout`. Al
filtrar, el iframe encoge pero esa reserva no, y queda el hueco en blanco antes
del pie.

El catálogo lo colapsa él mismo (`colapsarContenedores`), con `!important`
porque la reserva del constructor también lo lleva. Es el mismo tratamiento que
tu código global aplica a los bloques que sí reconoce; `#cpm-catalogo` no está
en su lista, así que tiene que hacerlo solo.

La ficha de propiedad se ancla **debajo** de la cabecera fija del sitio. Esa
altura se mide en el documento del sitio, no en el del bloque —medirla dentro
del iframe daba siempre 0, y por eso el botón de cerrar acababa tapado por la
cabecera en móvil. El desplazamiento de la barra de filtros, en cambio, sólo se
aplica fuera de un iframe: dentro, `position:sticky` no puede pegarse a nada y
lo único que consigue es taparle la primera fila de tarjetas.

## Pendiente

- **Confirmar las rutas de respaldo** de la tabla de arriba. Mientras el menú
  del sitio tenga esos destinos, se usan los del menú y el respaldo no llega a
  usarse; sólo importa si alguna división no aparece en la navegación.
- **`assets/logo-cuprum-cropped.jpg`** viene recortado de origen: le falta la
  "M" final de "CUPRUM". Hay que reemplazarlo por el logotipo completo
  (mismo nombre de archivo, o actualizar la ruta en `index.html`).
  El CSS ya lo ajusta solo, sin importar el tamaño.

## Datos que se editan a mano

Están en `index.html`, todos como texto plano:

| Qué | Dónde buscar |
| --- | --- |
| Teléfonos de WhatsApp | `wa.me/52...` (5 apariciones) y `WA_NUMBER` en el script |
| Correo | `ventas@hemca.com.mx` |
| Cifras (12+, 500+, …) | sección `class="metrics"` |
| Servicios, proyectos, proceso | secciones `#servicios`, `#proyectos`, `#proceso` |
| Dominio para SEO / redes | etiquetas `canonical` y `og:` en el `<head>` |

El año del pie de página se actualiza solo.
