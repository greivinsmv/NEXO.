# ADR-004: seleccionar juegos con dos precios observados

**Estado:** aceptado

## Contexto

El enunciado exige al menos 500 juegos publicados con precio de dos tiendas. El catálogo anterior tenía 500 juegos populares de Steam, pero 121 solo tenían una oferta guardada. Una lista más grande por sí sola no resuelve esa condición.

## Decisión

Mantener SteamSpy como listado público paginado y ordenar sus candidatos por actividad, propietarios estimados y votos. Complementar sus páginas con los juegos activos del catálogo anterior para que un cambio brusco en el ranking no elimine títulos relevantes. Antes de validar fichas en Steam Store, comprobar mediante CheapShark si hay una oferta de otra tienda activa. Si una tienda no reaparece en la captura, se puede conservar su última oferta observada durante siete días como máximo, con su fecha original. Elegir los primeros 500 candidatos que sean juegos de pago disponibles, tengan precio de Steam y una segunda oferta reciente. Guardar la selección, las ofertas y sus fechas en una transacción de SQLite. Si no se validan 500 o falla la captura, conservar el catálogo anterior. La tarea semanal reconstruye el catálogo y una tarea manual permite repetirla.

Las ofertas de CheapShark se identifican como datos del agregador y conservan su enlace de redirección. Un precio obtenido por ese medio no se presenta como scraping HTML directo de la tienda; las fuentes HTML y el minorista del enunciado siguen pendientes.

## Alternativas

- Publicar juegos con un solo precio: deja 121 fichas sin comparación.
- Agregar cualquier precio sin validar el juego y la tienda: puede asociar ediciones diferentes.
- Mantener los 500 títulos originales aunque algunos dejen de estar disponibles: incumple el criterio de disponibilidad.

## Consecuencias

Algunos títulos del catálogo anterior pueden salir y entrar otros con mayor cobertura de precios. El ranking conserva la relevancia dentro de los juegos comparables; no afirma que un precio de PC sirva para consolas. Una oferta conservada puede tener hasta siete días, dato visible en la ficha. La fuente agregada permite verificar dos precios, pero no sustituye la integración directa de las tiendas y del minorista requeridos para la entrega.
