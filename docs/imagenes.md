# Portadas y capturas de NEXO

## Ahora

El piloto usa las portadas públicas de Steam CDN identificadas por `steamAppID`. Se han comprobado las ocho URLs del piloto. Si una imagen falla, la interfaz muestra su fondo y título. Los precios de CheapShark y la portada de Steam tienen procedencias distintas.

## Plan para 500 juegos

- Guardar en la base únicamente `cover_url`, hasta seis `screenshot_url`, fuente, ID de juego en esa fuente y fecha de verificación. Las imágenes ordinarias se sirven desde el CDN de la fuente, no desde GitHub.
- Preferir metadatos e imágenes de [IGDB API](https://api-docs.igdb.com/) para juegos de varias plataformas, o la portada de Steam cuando haya AppID. IGDB documenta tamaños de portada y capturas; requiere credenciales en el pipeline, nunca en el navegador. Revisar sus condiciones de uso antes de publicar a escala.
- Usar portada pequeña en el catálogo y tamaño mayor solo en la ficha; `loading="lazy"` en tarjetas y capturas fuera de pantalla. El catálogo muestra 24 juegos por lote para limitar el DOM.
- Cargar las capturas solo al abrir la ficha, máximo seis iniciales. Una imagen que falle deja un espacio de reserva o se omite; el precio y la ficha siguen funcionando.
- Mantener en almacenamiento de objetos únicamente las excepciones aprobadas manualmente por un administrador. El repositorio conserva código y metadatos, no miles de archivos de imagen.

Para corregir una portada antes de tener panel administrativo, se revisa la URL en la fuente del catálogo, se actualiza el registro de SQLite y se vuelve a exportar `data/catalog.json`. La corrección debe conservar su procedencia.

La web pública no permite subir archivos. GitHub Pages es solo lectura para visitantes.

## Panel administrativo posterior

El panel requerirá inicio de sesión y autorización del rol `admin` **en el servidor para cada operación**. La API validará tipo real de archivo (JPEG, PNG o WebP), peso, dimensiones y cantidad; convertirá a WebP, quitará metadatos, guardará en almacenamiento de objetos y registrará autor, fecha, juego y procedencia. Los archivos no se servirán desde una ruta que ejecute código. Cada cambio tendrá historial y opción de revertir. Un usuario común no podrá subir ni sustituir imágenes aunque conozca la URL del endpoint.

Además de portada, el modelo podrá guardar una galería de capturas con orden, texto alternativo y fuente. Una captura incorrecta no se sustituirá silenciosamente: se conservará el registro del cambio.
