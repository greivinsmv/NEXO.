# ADR-005: acceso responsable a fuentes HTML

**Estado:** aceptado para el prototipo; revisar antes de la entrega.

## Contexto

El enunciado pide tres fuentes HTML, dos de ellas tiendas, y al menos un minorista. También exige revisar `robots.txt` y las condiciones de uso, sin evadir bloqueos. El catálogo actual usa Steam Store y el catálogo público de GOG para precios directos, además de CheapShark para otras tiendas; todavía no cumple el mínimo de HTML ni el minorista.

## Evidencia revisada el 16 de noviembre de 2026

- [Steam `robots.txt`](https://store.steampowered.com/robots.txt) no excluye `/app/`, pero algunas fichas devuelven una página de verificación de edad sin precio. El [acuerdo de Steam](https://store.steampowered.com/subscriber_agreement/) contiene restricciones de automatización; se mantiene su API pública como fuente de producción y no se elude la verificación de edad.
- [GOG `robots.txt`](https://www.gog.com/robots.txt) no excluye `/en/game/`, pero su [acuerdo de usuario](https://support.gog.com/hc/en-us/articles/212632089-GOG-User-Agreement) restringe bots, scripts y herramientas de extracción que interactúan con el servicio. La visibilidad en `robots.txt` no autoriza una captura masiva. También hay que revisar si esa restricción alcanza el catálogo JSON que hoy consulta NEXO.
- [Walmart `robots.txt`](https://www.walmart.com/robots.txt) permite una ficha `/ip/` consultada como muestra, pero sus [condiciones de uso](https://www.walmart.com/help/article/walmart-com-terms-of-use/3b75080af40340d6bbd596f116fae5a0/) prohíben recopilar materiales mediante robots o scraping sin consentimiento previo por escrito.
- Metacritic publica un Metascore explícito en JSON-LD de sus fichas y su `robots.txt` no excluye todas las páginas de producto; su pie enlaza las [condiciones de Fandom](https://www.fandom.com/terms-of-use), que restringen el scraping de contenido. No se considera permiso para un barrido completo.
- [Best Buy Products API](https://developer.bestbuy.com/apis) ofrece precios y disponibilidad de su catálogo mediante una API oficial. Sus [condiciones](https://developer.bestbuy.com/legal) requieren cuenta y clave de desarrollador válida. Es una alternativa concreta para el minorista, sujeta a verificar que el uso educativo previsto cumpla esas condiciones y a registrar la sustitución de HTML en este ADR. No se dispone de la clave en el proyecto.

Se hicieron consultas aisladas para verificar estructuras HTML. `scripts/html_sources.py` extrae datos explícitos de Steam, GOG, Walmart y Metacritic; sus pruebas comprueban precios, ediciones, estado nuevo y calificación. **No hay una tarea de captura masiva de esos HTML.**

## Decisión

Conservar los parsers como prototipo verificable y no ejecutar un barrido HTML de GOG, Walmart o Metacritic sin una base de uso permitida. Para completar el requisito, el equipo debe elegir fuentes equivalentes cuyos términos permitan el acceso previsto, obtener autorización de las fuentes, o justificar una sustitución por API oficial donde lo admite el enunciado. La integración del minorista requiere distinguir plataforma, edición y formato antes de sumar su precio a una ficha; una copia física de PlayStation no se comparará como si fuera la clave digital de PC.

## Alternativas y consecuencias

- Automatizar páginas solo porque `robots.txt` las permite: descartado por las condiciones de uso identificadas.
- Incorporar precios HTML observados una vez como si fueran actuales: descartado; cada dato necesita fecha y estado de actualización.
- Usar las APIs y capturas agregadas existentes mientras se resuelve el acceso HTML: mantiene el sitio útil, pero **no satisface por sí solo** los mínimos de HTML y minorista de la rúbrica.

La selección de fuentes deberá registrarse en un ADR nuevo o en una revisión de este documento, con evidencia de acceso y límites, antes de activar capturas masivas.
