# ADR-003: plataformas de lanzamiento enlazadas por ID

**Estado:** aceptado

## Contexto

La etapa 0 identifica 500 juegos por su ID de Steam, pero Steam Store solo informa sistemas de PC. El enunciado pide al menos tres familias de plataformas entre PC, PlayStation, Xbox y Nintendo Switch. Vincular por título mezclaría remasterizaciones, secuelas y ediciones diferentes.

## Decisión

Consultar en lotes las afirmaciones públicas de Wikidata que unen el ID de Steam (`P1733`) con las plataformas de lanzamiento (`P400`). Aceptar únicamente IDs asociados a un único juego de Wikidata; descartar las asociaciones ambiguas. Convertir identificadores conocidos de consolas a las familias PlayStation, Xbox, Nintendo Switch y Nintendo Switch 2, conservando el ID de origen y la fecha de captura en SQLite. Mantener PC como plataforma confirmada por Steam. Cachear respuestas durante siete días y publicar una actualización transaccional semanal.

Wikidata complementa la metadata de Steam y no sustituye las tiendas de precios exigidas. Las familias de lanzamiento se usan en el filtro, mientras las ofertas actuales siguen siendo de PC y así se indican en la interfaz. Nintendo Switch 2 se mantiene separada porque un lanzamiento para esa consola no demuestra compatibilidad con Switch.

## Alternativas

- Inferir plataforma por nombre o portada: ambiguo para ediciones y remasterizaciones.
- Consultar una API comercial de juegos: requiere una clave o una cuota externa para actualizar los 500 títulos.
- Dejar solo PC: no cumple la cobertura de plataformas del enunciado.

## Consecuencias

La cobertura depende de afirmaciones comunitarias; un juego sin entrada o con dos entradas se queda solo con PC hasta que se verifique. Este paso no aporta precios de consola ni reemplaza las fuentes HTML y el minorista pendientes. `scripts/audit_requirements.py` mide la cobertura sin convertir una asociación ambigua en un dato publicado.
