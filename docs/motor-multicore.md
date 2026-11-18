# Motor y requisitos del enunciado

El enunciado distingue tres modos **del mismo pipeline**:

| Modo | Descarga | Emparejamiento de títulos |
| --- | --- | --- |
| `sequential` | Un trabajo a la vez | En el hilo principal |
| `concurrent` | Hilos con colas acotadas | En el hilo principal |
| `parallel` | Los mismos hilos y colas | Procesos en varios núcleos |

`scripts/pipeline.py` ejecuta esos tres modos con la misma lista de trabajos y el mismo parser. Sus colas tienen tamaño configurable, igual que el número de workers de E/S y CPU. `scripts/title_matching.py` normaliza títulos y calcula similitud de tokens y distancia de edición en Python puro. Una edición distinta, dos candidatos cercanos o un resultado cercano al umbral quedan como dudosos. El umbral actual es **provisional**: todavía falta el conjunto de al menos 60 pares revisados manualmente que exige el curso.

El transporte `live` de `scripts/run_pipeline.py` usa HTTPS, timeout, reintentos con backoff y jitter, un semáforo y un intervalo de consultas por dominio. Puede guardar las respuestas originales. El transporte `replay` lee esas mismas respuestas guardadas y añade latencia fija o con variación determinista. La interfaz de parser recibe los mismos bytes en ambos casos. Un trabajo fallido se reintenta al final y se registra en las métricas.

```bash
python scripts/run_pipeline.py --manifest trabajos.json --transport replay \
  --fixture-root capturas --mode parallel --io-workers 4 --cpu-workers 2 \
  --latency-ms 80 --jitter-ms 20 --output medicion.json
python -m unittest discover -s scripts -p 'test_*.py'
```

Cada entrada del manifiesto indica `game` (`steamAppId`, `name`, `altTitles`), `source` y `fixture`; en vivo también `url`. La prueba sin red usa pequeñas respuestas **sintéticas** para comprobar que los tres modos producen los mismos emparejamientos. `scripts/capture_replay.py` construye además un corpus local con las respuestas JSON de Steam Store y CheapShark para los 500 juegos publicados, y guarda el listado paginado de SteamSpy de la etapa 0. Las respuestas de Steam proceden de la caché reciente del importador o se descargan si vencieron; el importador de Steam conserva el JSON decodificado y serializado. Las respuestas de CheapShark se guardan como bytes originales. Cada archivo tiene un SHA-256 en `data/replay/metadata.json`. El directorio de capturas queda fuera de Git y se reconstruye con:

```bash
python scripts/capture_replay.py
python scripts/run_pipeline.py --manifest data/replay/manifest.json --transport replay \
  --fixture-root data/replay --mode parallel --io-workers 4 --cpu-workers 2 \
  --latency-ms 80 --jitter-ms 20 --output resultados/replay.json
```

Esta captura cubre dos fuentes reales para los 500 juegos. Todavía no cubre todas las fuentes obligatorias del experimento formal ni constituye las cinco mediciones por configuración.

Para medir la etapa de cálculo con más trabajo, `scripts/build_replay_pool.py` forma un listado de candidatos únicos a partir de esas respuestas reales. Cada uno de los 500 juegos se compara contra el listado completo; no se inventan títulos. El manifiesto ampliado se usa solo en replay:

```bash
python scripts/build_replay_pool.py
python scripts/run_pipeline.py --manifest data/replay/expanded-manifest.json \
  --transport replay --fixture-root data/replay --mode parallel \
  --io-workers 4 --cpu-workers 2 --output resultados/replay-ampliado.json
```

Para repetir el barrido de los 500 juegos y sus respuestas originales, usar cinco repeticiones por configuración. El CSV incluye tiempos por etapa, medianas, extremos, speedup, eficiencia y Karp–Flatt:

```bash
python scripts/benchmark_pipeline.py --manifest data/replay/manifest.json \
  --fixture-root data/replay --output resultados/replay-fijo.csv \
  --repetitions 5 --latency-ms 10 --jitter-ms 0
python scripts/benchmark_pipeline.py --manifest data/replay/manifest.json \
  --fixture-root data/replay --output resultados/replay-variable.csv \
  --repetitions 5 --latency-ms 10 --jitter-ms 2
```

La captura semanal existente de CheapShark usa `scripts/update_store_offers.py --mode threads --workers 4`: consulta los 500 IDs en lotes de 20, respeta un intervalo global de 2,5 segundos por intento y solo reemplaza SQLite después de completar y validar todos los lotes. También puede ejecutarse en modo `sequential` o `processes` como herramienta de una sola fuente. **No se presenta esa herramienta como el pipeline completo del enunciado.**

## Experimento de contención

`scripts/benchmark_contention.py` cuenta las ofertas reales guardadas en SQLite por plataforma. Compara un lock global por incremento, contadores locales por hilo combinados al final y una cola concurrente. Comprueba que las tres entregan el mismo recuento, registra cinco repeticiones con mediana y extremos, y permite variar trabajadores y tamaño de entrada. También reproduce una carrera sin lock: dos barreras obligan a varios hilos a leer el mismo valor antes de escribirlo, por lo que se pierden incrementos. Ese control hace el fallo repetible sin depender del azar del planificador.

```bash
python scripts/benchmark_contention.py --workers 4 --repeat-input 20 \
  --repetitions 5 --output resultados/contencion-4.json
```

El resultado de esta herramienta sirve para el experimento de contención. El informe final debe incluir las mediciones del equipo en su propia máquina y explicar el coste de las tres estrategias; aquí no se atribuyen a los integrantes resultados medidos en otro entorno.

## Pendiente para la entrega

- Capturar respuestas HTML/JSON reales de las demás fuentes para los 500 juegos y escribir sus parsers. El núcleo ya interpreta el JSON real de Steam Store y CheapShark, además del formato normalizado de pruebas.
- Añadir a la etapa 0 el listado paginado dentro del mismo replay y cubrir al menos dos tiendas de plataforma, un minorista y tres fuentes HTML.
- Revisar manualmente 60 pares, incluidos 50 casos difíciles, para fijar el umbral y medir precisión y exhaustividad.
- La herramienta `scripts/validate_matching.py` lee un CSV revisado por el equipo con columnas `canonical,candidate,alternatives,expected,difficult`; `expected` es 1 si es el mismo producto y 0 si no, `alternatives` separa títulos equivalentes con `|`. Rechaza muestras menores de 60 pares o 50 casos difíciles y reporta la matriz de confusión, precisión y exhaustividad. No se incluye una muestra inventada.
- `python scripts/prepare_title_review.py` prepara una cola de 60 pares observados en CheapShark: 30 variantes del mismo ID, 20 títulos similares de otro ID y 10 controles exactos. Marca 50 casos para revisión difícil. La columna `suggested` es una pista automática; **`expected` queda vacía** hasta que el equipo revise el producto y la edición. Después se copia el CSV revisado y se ejecuta `python scripts/validate_matching.py archivo-revisado.csv`.
- Ejecutar barridos con cinco repeticiones por configuración, mediciones por etapa, speedup absoluto y relativo, eficiencia y Karp–Flatt; registrar equipo y dispersión.
- Medir el experimento de contención en la máquina del equipo, analizarlo y publicar métricas reales en el sitio.
