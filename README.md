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

Además de la página suelta de HEMCA, hay tres bloques pensados para pegarse
en un contenedor de código del constructor. No llevan etiquetas de documento,
todo su CSS está acotado a su propio contenedor y no dependen de ningún CDN
de scripts.

| Archivo | Va en | Contenedor |
| --- | --- | --- |
| `hemca-embed-hostinger.html` | la página de HEMCA | `.hemca` |
| `portafolio-hms-embed.html` | el portafolio de Hummingbird | `#hbp` |
| `divisiones-embed-hostinger.html` | `/divisiones` | `#cpm-divisiones` |

Se construyen con `tools/` (`css_prep.py`, `div_prep.py`, `build.py`); no se
editan a mano, porque el guion vuelve a generarlos desde el original.

### Destinos de los enlaces en Divisiones

El bloque de divisiones enlaza al resto del sitio. Para no depender de rutas
escritas a mano, **busca cada destino en el menú real del sitio** y enlaza
donde enlaza tu propia navegación; sólo si no lo encuentra usa una ruta de
respaldo. Las rutas de respaldo están en una sola tabla, `DESTINOS`, dentro de
`tools/build.py`:

| Destino | Se busca en el menú como | Respaldo |
| --- | --- | --- |
| Construcción | construcción / construcción y desarrollo | `/construccion` |
| Inmobiliaria | inmobiliaria / servicios inmobiliarios | `/servicios-inmobiliarios` |
| Legal | legal / división legal / jurídico | `/division-legal` |
| Marketing | marketing / hummingbird | `/marketing` |
| Contacto | contacto / contáctanos | `/contacto` |
| Propiedades | propiedades / inmuebles | `/catalogo-de-propiedades` |

Todos abren en la ventana completa (`target="_top"`), no dentro del iframe.

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
