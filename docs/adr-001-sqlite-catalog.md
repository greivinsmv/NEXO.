# ADR-001: SQLite como repositorio de juegos

**Estado:** aceptado

## Contexto

El enunciado exige al menos 500 juegos en una base de datos local o en la nube. La lista no puede estar escrita directamente en el código y debe poblarse automáticamente desde un listado público paginado. NEXO se publica en GitHub Pages, que sirve archivos estáticos y no ejecuta consultas SQL.

## Decisión

Usar `data/nexo.sqlite` como fuente de datos del catálogo. `scripts/build_catalog.py` importa las páginas 0 y 1 del listado público de SteamSpy como etapa 0, registra candidatos y procedencia, valida juegos con Steam Store y guarda 500 juegos o más en SQLite. `scripts/catalog_db.py` exporta `data/catalog.json` desde la base. La web descarga ese JSON; los archivos JavaScript no contienen una lista de juegos.

La base y su exportación se guardan en el repositorio para conservarlas entre ejecuciones. El importador se ejecuta localmente con Python, que ya incluye `sqlite3`; después se publican los dos archivos juntos. GitHub Actions verifica el resultado con permisos de solo lectura. La base contiene únicamente datos públicos del catálogo y URL de imágenes, nunca credenciales ni usuarios.

## Esquema

- `catalog_runs` y `stage0_candidates`: captura, URL del listado, páginas consultadas y posición de cada candidato.
- `games`: identificador Steam, nombre, precio de referencia, relevancia, campos principales y datos completos de la ficha.
- `game_genres`, `game_screenshots`, `game_achievements`: información relacionada por identificador Steam.
- `price_observations`: precio de Steam observado en cada actualización, con fecha de captura.

La actualización es transaccional. Si no se validan 500 juegos o no se obtienen dos páginas de candidatos, no se reemplaza el catálogo publicado.

## Consecuencias

SQLite evita administrar un servidor para esta entrega y satisface el requisito de base local. GitHub Pages solo lee el JSON generado; el archivo SQLite no se consulta desde el navegador. Las ediciones en tiempo real y cuentas de administrador requerirán una API y una base alojada, por ejemplo PostgreSQL. Firebase también permitiría escrituras remotas, pero añade servicios y reglas de acceso que este catálogo público de lectura no necesita.

## Comprobación

`python scripts/build_catalog.py` actualiza la base y el JSON. Para revisar el resultado sin instalar la herramienta `sqlite3`:

```bash
python -c "import sqlite3; c=sqlite3.connect('data/nexo.sqlite'); print(c.execute('select count(*) from games where active=1').fetchone()[0]); print(c.execute('select distinct source_page from stage0_candidates order by source_page').fetchall())"
```
