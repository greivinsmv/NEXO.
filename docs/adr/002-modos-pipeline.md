# ADR-002 · Modos del pipeline · 15 de noviembre de 2026

**Estado:** propuesto; pendiente de medir en el replay completo.

**Contexto.** El enunciado exige aislar el beneficio de solapar E/S del beneficio de repartir el emparejamiento entre núcleos. Las descargas esperan la red; el cálculo de similitud en Python puro consume CPU y está limitado por el GIL en hilos.

**Alternativas.** (1) Hilos para todas las etapas: sencilla, pero no da paralelismo de CPU en Python. (2) Procesos para todas las etapas: permite CPU paralela, pero añade serialización y procesos a la E/S. (3) Hilos para descargar y procesos solo para emparejar.

**Decisión.** Usar una misma lista de trabajos y parser en tres configuraciones: secuencial; E/S con `ThreadPoolExecutor`/colas acotadas y emparejamiento serial; y la misma E/S con `ProcessPoolExecutor` para emparejar. El transporte de replay cambia los bytes de entrada, sin cambiar el algoritmo.

**Consecuencias.** El modo completo paga la serialización de candidatos y creación de procesos. La ganancia depende del volumen de candidatos, núcleos y tamaño de lotes. Se medirá con el barrido formal; el núcleo actual todavía no cubre todas las fuentes reales ni la etapa 0 en replay.
