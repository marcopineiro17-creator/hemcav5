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

Además de la página suelta de HEMCA, hay ocho bloques pensados para pegarse
en un contenedor de código del constructor. No llevan etiquetas de documento
y todo su CSS está acotado a su propio contenedor. Seis no dependen de ningún
recurso externo; el mapa y el portafolio de asesores sí —Leaflet y Firebase—,
y por eso el del mapa lleva su propia lista blanca de orígenes.

| Archivo | Va en | Contenedor |
| --- | --- | --- |
| `hemca-embed-hostinger.html` | la página de HEMCA | `.hemca` |
| `portafolio-hms-embed.html` | el portafolio de Hummingbird | `#hbp` |
| `divisiones-embed-hostinger.html` | `/divisiones` | `#cpm-divisiones` |
| `inicio-embed-hostinger.html` | la portada | `#cpm-home` |
| `catalogo-embed-hostinger.html` | `/catalogo-de-propiedades` | `#cpm-catalogo` |
| `predios-embed-hostinger.html` | `/regularizacion-predios` | `#cpm-predios` |
| `mapa-embed-hostinger.html` | el mapa de la cartera | `#cpm-mapa` |
| `portafolio-asesores-embed-hostinger.html` | el portafolio privado de asesores | `#cpm-portafolio` |

Se construyen con `tools/` (`css_prep.py`, `div_prep.py`, `home_prep.py`,
`cat_prep.py`, `predios.py`, `mapa.py`, `portafolio_prep.py`, `build.py`); no se editan a mano, porque el guion vuelve a generarlos desde el
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

- `WHATSAPP`. Ya está puesto: `529995690047` (999 569 0047), el mismo número
  que atiende HEMCA en el sitio. Si se vacía, los botones no se rompen: llevan
  a la página de contacto.
- `FOTOS`. Ocho huecos, ya con las imágenes del CDN de Hostinger puestas:
  `portada`, `escritura`, `hipoteca`, `alcance`, `alcance2`, `cierre`,
  `insejupy` y `desarrollo`. **Un hueco vacío no se ve vacío:** debajo hay una
  ilustración vectorial —el plano de subdivisión que se dibuja solo, la
  escritura con su sello, el gravamen cancelándose— hecha para sostenerse
  sola, y la foto sólo la sustituye cuando existe. Vaciar `insejupy` y
  `desarrollo` devuelve el sello giratorio del bloque azul.

  **La maqueta está hecha para la orientación de cada foto**, así que cambiar
  una por otra de orientación distinta obliga a revisar su hueco: `portada` es
  horizontal, las de casos y alcance verticales, y `cierre` apaisada. Las
  fotos llevan un tinte azul muy leve (20 %) para dar unidad de marca; la del
  cierre no lleva ninguno —va como banda limpia, sin velo ni degradado—.

Del movimiento: los trazos de los planos se dibujan con `stroke-dashoffset`,
los sellos caen y se asientan, la línea del proceso se llena según avanzas
—medida contra el recorrido de la sección por la pantalla, no contra su
distancia al borde, que llenaba la barra de golpe— y las fotos llevan un
paralaje corto. Nada de `backdrop-filter` ni de rotaciones sobre superficies
grandes: medido en la réplica y con las fotos puestas, 60 fps y 1 fotograma lento de 144.

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

### Portafolio de asesores

Es la cartera privada: se entra con una cuenta de CPM y de ahí salen las
fichas en PDF. `tools/portafolio_prep.py` parte de
`src/cpm-portafolio-original.html` y le hace cuatro cosas.

**Coordenadas.** Junto al enlace de Maps hay ahora un campo propio. Acepta
las tres formas en que se puede copiar una ubicación:

| Lo que se pega | Ejemplo |
| --- | --- |
| dos números | `21.067187, -89.504562` |
| un Plus Code | `3F8W+V5` (lo que se copia del móvil) |
| un enlace **largo** de Maps | `.../@21.0203,-89.5871,15z` |

Los enlaces cortos (`maps.app.goo.gl`) no llevan las coordenadas dentro, así
que de ellos no se puede sacar nada; el campo lo dice en vez de callarse. El
Plus Code corto se completa con la localidad de la propiedad, y por eso la
ciudad tiene que estar escrita: si no está en el cuadro, el aviso lo explica y
pide el código completo. El cálculo y las tablas de localidades son
literalmente los del mapa —`tools/portafolio_prep.py` los saca de
`tools/mapa_js.txt` al construir—, para que las dos páginas no se desajusten.

Lo capturado se guarda como `lat`/`lng` en el documento del inmueble, y esos
dos campos están ya en `CAMPOS_PUBLICOS`: al sincronizar viajan a
`catalogo_publico`, que es de donde los lee el mapa. Si una propiedad tenía
coordenadas puestas antes desde el mapa, la sincronización **las adopta** en
vez de borrarlas —el espejo se escribe con `set()`, que reemplaza el
documento entero— y las sube al inmueble, que manda desde entonces.

**Exclusivas.** Se ven en la vista del asesor, con las mismas fichas y el
mismo PDF que las demás, y con un sello de *Exclusiva* en la tarjeta y una
línea en la ficha diciendo lo único que hay que saber: que no se publican.
Antes solo las veía un administrador.

Y una propiedad cuenta como exclusiva si **cualquiera** de sus categorías
contiene «exclusiv», no solo si dice exactamente `Exclusivos (no publicar)`.
Esto importa: las etiquetadas antes de que existiera esa opción —`Exclusiva`,
`EXCLUSIVOS`— contaban como normales, así que **se publicaban**. La
sincronización las saca del catálogo público en la siguiente pasada.

**Revisión** (botón de administrador). Un cuadro por propiedad con lo que hay
guardado de verdad: el campo `categorias` tal cual, si cuenta como exclusiva,
su estado, si es publicable, si está ahora mismo en el catálogo público y si
tiene coordenadas. Debajo, el informe en texto para copiar. Es la forma de
contestar «¿qué pasó con esa propiedad?» con datos y no con suposiciones.

**Un dato mal puesto ya no esconde la cartera entera.** El listado de
Firestore recorría los documentos sin red: si uno solo hacía saltar una
excepción —por ejemplo `categorias` guardado como texto en vez de arreglo—,
la excepción salía del *callback* de `onSnapshot`, la lista se quedaba como
estaba y la rejilla no se volvía a pintar. Ahora el documento malo se salta,
se cuenta y aparece en el panel de revisión.

También se corrigió que `isAdmin()` comparaba el correo distinguiendo
mayúsculas contra una lista en minúsculas: una cuenta dada de alta como
`Marco@…` se quedaba sin ser administradora.

### Lo que se arregló después de probarlo en un teléfono

**El botón de cerrar la ficha no se alcanzaba.** Es el mismo defecto que ya
tenía el catálogo: la ficha se ancla a la banda visible del marco, pero esa
banda se medía desde el borde de la ventana, **sin descontar la cabecera fija
del sitio** —64 px en móvil—, así que la cabecera de la ficha, que es donde
vive el botón, quedaba justo debajo de ella. Dos cambios: la banda empieza
debajo de la cabecera (medida en el documento del **sitio**, no en el del
bloque, donde siempre daría cero), y la cabecera de la hoja es **pegada**, así
que el botón sigue ahí aunque se desplace el contenido. Ahora mide 44×44 —el
mínimo con el que un dedo acierta— y además **Escape** cierra.

**El PDF.** Tres cosas distintas, todas medidas:

1. *Salía sin fotos.* La receta habitual —abrir una ventana en blanco y
   escribirle el documento— produce un documento que **no llega a pedir las
   imágenes**: cero peticiones, comprobado. Ahora el documento se sirve en una
   dirección `blob:`, que sí carga; con ventana en blanco no cargaba ninguna y
   con `blob:` cargan todas.
2. *Tardaba ocho segundos.* Se esperaba a las fotos mirando `complete` en un
   bucle con tope de 8 s, y una petición colgada nunca pone `complete` a
   `true`: había que agotar el tope entero. Ahora se escuchan `load` y `error`
   de cada foto, con tope de 3,5 s. Medido: de 8 s a 0,2 s.
3. *Si el navegador bloqueaba la ventana, no pasaba nada de nada.* El código
   hacía `if(!w) return;`. Dentro de un iframe con `sandbox` eso pasa siempre.
   Ahora hay tres caminos: ventana nueva → marco oculto → la hoja en pantalla
   con su botón de imprimir. Los tres comprobados, incluido el caso en que
   además `print()` está prohibido.

Y el botón avisa mientras prepara («⏳ Preparando la ficha…»): sin eso, la
espera se lee como que no pasó nada y se vuelve a pulsar.

**El botón de ubicación del PDF.** Era un enlace sin `target`: al pulsarlo, la
ventana de la ficha se iba a Google Maps y se perdía el documento. Y un PDF ya
guardado pierde los enlaces en muchos visores. Ahora el enlace abre en pestaña
nueva **y** debajo van la dirección y las coordenadas escritas, que se leen y
se teclean aunque el enlace no funcione. El de la ficha en pantalla también:
dentro de un iframe con `sandbox`, `target="_blank"` no abre nada, así que si
el navegador lo impide se navega la ventana completa.

**Interfaz.** El velo de las ventanas llevaba `backdrop-filter`, que cuesta
fotogramas incluso cuando no se ve —ya medido en otros bloques de este
sitio—: fuera, y el velo va más oscuro. La ficha repetía la superficie en dos
cuadros contiguos («SUPERFICIE 256 m²» y «M² 256»): ahora el m² suelto solo
sale cuando la superficie va en hectáreas, y en su lugar aparece si la
propiedad tiene coordenadas. Con una ventana abierta el sitio ya no se
desplaza por detrás (y se destraba solo si algo fallara). Las tarjetas se
abren con el teclado y sus fotos cargan cuando hacen falta. Los botones de la
barra pasan de 26 px a 40 en móvil, y el de quitar una foto de 20 a 28. La
galería se mueve con las flechas. La lupa del buscador se centra respecto a su
caja en vez de con un ajuste a mano que solo cuadraba con un relleno concreto.

Comprobado con Firebase imitado —no hay salida a internet desde donde se
construye— sobre una cartera con los casos que importan: una exclusiva con la
etiqueta de hoy, otra con la etiqueta vieja ya colada en el catálogo público,
una con `categorias` guardado como texto, una con coordenadas solo en el
espejo, un huérfano en el catálogo y un documento ilegible. Con sesión de
administrador y con sesión de asesor, en escritorio y en móvil, y dentro de
una réplica del contenedor de Hostinger **con su cabecera fija**, que es lo
que hacía falta para reproducir lo del botón de cerrar.

### Mapa de propiedades

Lee la colección pública `catalogo_publico` de Firebase —la misma que el
catálogo— y pinta la cartera sobre un mapa navegable con la lista
sincronizada: al pasar por una tarjeta se resalta su alfiler, al pulsar un
alfiler se resalta y se trae su tarjeta, y **Buscar en esta área** acota la
lista a lo que se ve en el mapa. Se escribe en `tools/mapa_css.txt`,
`mapa_html.txt` y `mapa_js.txt`, y `tools/mapa.py` las une y las revisa.

Es el único bloque que **sí depende de recursos externos**: Firebase para
leer la cartera y Leaflet con las teselas del mapa. La revisión los permite
por lista blanca, con su motivo cada uno, y sigue rechazando cualquier otro
origen. Si Leaflet no carga, el bloque no se queda en blanco: pasa a lista y
lo dice.

#### Las dos capas

Arranca en **satélite**, que es lo que se pide para ver un terreno: la
vegetación, los techos, las bardas. Un botón arriba a la derecha cambia a
**mapa de calles** y vuelve; el botón dice a dónde vas, no dónde estás —como
el recuadro de Google Maps— y la elección se recuerda en el navegador.

| Capa | De dónde salen las teselas |
| --- | --- |
| Satélite | imágenes de Esri (Maxar, Earthstar) **más** su capa de transporte encima, transparente, que devuelve las calles y sus nombres |
| Mapa | OpenStreetMap, la de siempre |

Tres cosas que conviene tener claras:

**No es la imagen de Google.** Sus teselas exigen la API de Google Maps, que
es de pago y además prohíbe sacarlas de su visor. Las de Esri se usan sin
clave y son de calidad equivalente en la península; lo que no se puede
imitar con teselas planas es el 3D de Google Earth, esto es la foto vista
desde arriba.

**El acercamiento máximo se queda en 18 «de verdad».** Al pedir más cerca de
lo que hay fotografiado, un servidor de imágenes no devuelve un error:
devuelve un cuadro gris que dice que no hay datos. Con `maxNativeZoom: 18`,
Leaflet **amplía** la última foto buena en vez de pedir una que no existe: se
ve algo más suave al máximo acercamiento, pero nunca un hueco gris. Si la
imagen de tus zonas aguanta el 19, subir ese número es una línea en
`tools/mapa_js.txt`.

**Si las imágenes no llegan, se vuelve solo al mapa de calles** y lo dice en
un aviso. Hacen falta diez teselas fallidas y ninguna buena, con un segundo y
medio de gracia: unas cuantas fallidas en el borde son normales y no deberían
cambiar la vista.

Igual que con OpenStreetMap, estas teselas son de uso razonable con
atribución —que el pie ya muestra, y cambia según la capa activa—. Si algún
día el tráfico crece, conviene pasar a un proveedor de pago; el cambio es el
cuadro `CAPAS` al principio del guion.

Comprobado con Leaflet imitado interceptando las peticiones: la forma de cada
URL (las de Esri van `{z}/{y}/{x}`, la fila antes de la columna, que es lo
fácil de equivocar), que las dos capas de satélite se piden y se pintan, que
al cambiar se retira la anterior y no se acumulan, que la atribución y el
botón cambian, que la elección se recuerda al volver, que la caída al mapa de
calles ocurre y avisa, y que en un teléfono el botón se queda en el icono y
no se monta encima de los otros controles.

También es el único de **altura fija** en vez de documento alto: un mapa
necesita altura real, y la lista tiene su propio scroll interno. Esa altura
se **mide** —barra + filtros + pie descontados de la ventana real— porque
adivinarla dejaba el bloque 100 px más alto que la pantalla de un teléfono,
donde los filtros se reparten en más filas.

#### El problema de las coordenadas

Todos los `ubicacion_maps` de la cartera son enlaces **cortos**
(`maps.app.goo.gl/…`), y un enlace corto **no contiene las coordenadas**:
hay que seguir su redirección para saberlas, y un navegador no puede
seguirla contra el dominio de Google. Sin resolverlo no habría ni un
alfiler.

Se resuelve con una cadena de precedencia, de más fiable a menos:

| Orden | De dónde salen | Precisión |
| --- | --- | --- |
| 1 | campos `lat`/`lng` del documento (o `latitud`/`longitud`, `geo`, GeoPoint) | exacta |
| 2 | campo `plus_code`, decodificado en el propio navegador | exacta (~14 m) |
| 3 | coordenadas dentro del enlace, si es un enlace **largo** (`@lat,lng`, `!3d!4d`, `q=`) | exacta |
| 4 | un Plus Code escrito dentro del enlace o del texto | exacta (~14 m) |
| 5 | centroide de la localidad, del cuadro `LOCALIDADES` | **aproximada** |
| 6 | nada: la propiedad sale en la lista pero no en el mapa | sin ubicar |

#### Plus Codes

Es lo más fácil de copiar desde Google Maps en el teléfono: aparece debajo
del nombre del sitio, con la forma `3F8W+V5 Conkal, Yucatán`. Se decodifican
**en el navegador, sin red ni API**: el algoritmo Open Location Code es puro
cálculo. Un código corto (el que empieza tras el `+` de la cuarta posición)
le falta los cuatro primeros caracteres, que se recuperan usando la localidad
de la propiedad como referencia — de ahí que el cuadro `LOCALIDADES` sirva
para dos cosas.

Comprobado por ida y vuelta sobre seis localidades de la cartera: desvío
máximo 7,7 m sobre celdas de 13,9 m, y un código corto recuperado da el mismo
resultado que su código completo. `3F8W+V5 Conkal` resuelve a
`21.067187, -89.504562`, que es exactamente lo mismo que `76HG3F8W+V5`.

Lo aproximado se marca: alfiler de borde discontinuo dorado, etiqueta en la
tarjeta y un aviso arriba de la lista con el recuento. Varias propiedades de
la misma localidad no se apilan: se reparten en espiral con el ángulo dorado,
siempre igual para la misma propiedad.

**Modo edición** es la otra vía para pasar de aproximada a exacta. La de
todos los días es el campo de coordenadas del portafolio de asesores, que las
guarda en el inmueble y no vuelve a pedir la contraseña; esta de aquí sigue
sirviendo para un arreglo rápido sobre el mapa, y lo que fije se conserva: la
sincronización del portafolio adopta esas coordenadas en vez de pisarlas. Se
entra con una cuenta de CPM, se elige la propiedad
y se fija su ubicación de dos formas —haciendo clic en el mapa, o pegando en
la caja **las coordenadas** (`21.0672, -89.5046`) **o el Plus Code**
(`3F8W+V5`)—. Eso guarda `lat`/`lng` en su documento de `catalogo_publico` y
el alfiler pasa a exacto para siempre. Pegar es más preciso que atinar con el
clic, y el Plus Code es lo que se puede copiar desde el móvil. Las reglas ya exigen sesión para escribir, así que el modo sólo
funciona con credenciales válidas.

Si algún día crece el tráfico, las teselas de OpenStreetMap tienen política
de uso razonable y conviene pasar a un proveedor de pago; el cambio es una
línea (`L.tileLayer`).

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
