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

## Pendiente

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
