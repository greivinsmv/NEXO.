# Fuentes y monedas de NEXO (investigación inicial)

## Estado

La web publica ofertas para los 500 juegos del catálogo cuando las fuentes informan disponibilidad, y conserva campos pendientes cuando faltan datos. Los precios publicados corresponden a EE. UU. y pueden variar por región.

`live-data.js` contiene una captura diaria de ocho juegos de PC de la [API pública de CheapShark](https://apidocs.cheapshark.com/), más tasas de la [API oficial de Hacienda](https://api.hacienda.go.cr/docs/). Además, el catálogo SQLite conserva capturas semanales del catálogo oficial de GOG y de las ofertas de otras tiendas que CheapShark publica para los 500 identificadores de Steam, consultados en lotes. CheapShark es un agregador; sus precios no son una lectura directa de cada tienda y sus enlaces utilizan la redirección oficial.

## Fuentes candidatas

| Dato | Fuente | Uso propuesto | Estado |
| --- | --- | --- | --- |
| Descubrimiento del catálogo | [Listado de ofertas de Steam](https://store.steampowered.com/search/?specials=1) | Catálogo público paginado y enlaces a productos | Candidato; revisar robots.txt y condiciones antes de automatizar |
| Precio de tienda oficial | [Steam](https://store.steampowered.com/search/?specials=1), [PlayStation Store](https://store.playstation.com/en-us/pages/deals/), [Xbox](https://www.xbox.com/en-US/games/browse/DynamicChannel.GameDeals) | Comparar precio, formato, plataforma, región y fecha | Candidatos; prueba controlada y revisión por dominio pendientes |
| Otra tienda de plataforma | [Epic Games Store](https://store.epicgames.com/sales-and-specials) | Precio y descuento de juegos de PC | Candidata; revisar límites y estructura antes de automatizar |
| Minorista | [Best Buy: ofertas de videojuegos](https://www.bestbuy.com/site/all-video-games-on-sale/video-games-on-sale/pcmcat1720708994350.c?id=pcmcat1720708994350) | Precio de juegos físicos o digitales; formato y disponibilidad | Candidato; revisar restricciones y disponibilidad por región |
| Precio de GOG | [Catálogo GOG](https://www.gog.com/en/games?tab=on_sale) | Ofertas oficiales para juegos coincidentes por título exacto | Captura paginada semanal de la API pública del catálogo |
| Precio de Eneba | [Eneba](https://www.eneba.com/) | Mercado de claves; requiere vendedor, región de activación y precio final | **No automatizar por ahora**: [API oficial](https://api.eneba.com/documentation/) limitada a vendedores; revisar condiciones antes de cualquier integración |
| Metadatos e imagen | [IGDB API](https://api-docs.igdb.com/) | Título, plataformas, fecha, portada, nombres alternativos | Requiere credenciales; nunca incluirlas en GitHub Pages |
| Calificación | [Metacritic](https://www.metacritic.com/game/), [OpenCritic](https://opencritic.com/) | Dos fuentes exigidas por el enunciado | Verificar condiciones y acceso antes de la captura |
| Duración | [HowLongToBeat](https://howlongtobeat.com/) | Historia, extras y completista | Obligatoria según el enunciado; acceso automatizado por validar |
| Cambio USD/EUR/CRC | [API del Ministerio de Hacienda de Costa Rica](https://api.hacienda.go.cr/docs/) | Dólar en colones; euro en dólares y colones | Fuente oficial candidata; capturar en el pipeline, no por cada visitante |

## Reglas de datos

1. Una oferta conserva `amount_original`, `currency_original`, `region`, `store`, `product_url`, `captured_at` y `status`. Una conversión no sobrescribe el valor original.
2. USD, EUR y CRC se convierten con una misma captura fechada de tasas. La interfaz muestra moneda de origen y fecha/tasa de conversión cuando el dato sea real.
3. El mejor precio solo se compara entre ofertas equivalentes por edición, plataforma, región y formato. No se mezclan claves de mercados de terceros con licencias directas sin etiquetarlas.
4. El descuento se calcula contra el precio regular de la misma oferta o contra un MSRP justificado, nunca contra un valor sin procedencia.
5. Si falla una fuente, conservar su última observación histórica, marcarla como desactualizada y excluirla del mejor precio actual.
6. La web estática recibe un JSON generado por el pipeline; no contiene claves privadas ni llama desde el navegador a fuentes que las requieran.

## Pendientes para ampliar las fuentes

- Incorporar fuentes directas para las demás tiendas y revisar sus condiciones por dominio.
- Confirmar región y moneda base de cada tienda. Priorizar Costa Rica cuando la tienda ofrezca precios locales; no convertir un precio de otra región como si estuviera disponible para Costa Rica.
- Capturar muestras pequeñas, validar selectores y documentar bloqueos o sustituciones en ADRs.
- Añadir alertas sobre cambios reales de precio. El historial de observaciones fechadas ya se conserva en SQLite.
