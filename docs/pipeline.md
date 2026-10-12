# Pipeline de datos — Motor de Demanda Rent-a-Car (SJO)

Este documento describe el flujo completo del pipeline de datos, de **fuente →
staging → marts → dashboard**, con sus **tests** y su **programación**.

## Diagrama del pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│  FUENTE (raw)                                                        │
│                                                                     │
│  src/generar_datos.py                                               │
│  └─ genera dataset SINTÉTICO realista (estacionalidad CR, feriados, │
│     Semana Santa, clases ACRISS, tarifas, canales, no-show).        │
│     Salida: data/raw/reservas_sinteticas.csv  (~57k reservas)        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGING (copia limpia, tipada y auditada)                           │
│                                                                     │
│  src/staging.py  +  sql/schema_staging.sql                          │
│  └─ limpieza (nulos, fechas, duración, tarifa, flags, duplicados)   │
│  └─ tipos explícitos + auditoría de carga (stg_carga)               │
│     Salida: data/staging/staging.db                                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  MARTS (modelo dimensional + agregados listos para análisis)        │
│                                                                     │
│  src/marts.py  +  sql/schema_marts.sql                              │
│  └─ Dimensiones: fecha, vehiculo, ubicacion, tarifa, canal, cliente │
│  └─ Hechos: fact_reservas (grano = reserva)                         │
│  └─ Agregados: mart_demanda_diaria, mart_noshow_canal,              │
│     mart_ingreso_categoria                                           │
│     Salida: data/marts/marts.db                                     │
└──────┬──────────────────────────┬───────────────────────────────────┘
       │                          │
       ▼                          ▼
┌─────────────────┐    ┌──────────────────────────────┐
│  ANÁLISIS       │    │  MODELOS                     │
│  analisis.py    │    │  modelo_no_show.py (logit+GB)│
│  (KPIs)         │    │  modelo_demanda.py (SARIMA)  │
└────────┬────────┘    └──────────────┬───────────────┘
         │                           │
         └─────────────┬─────────────┘
                       ▼
            data/processed/*.png
                       │
                       ▼
          ┌─────────────────────────┐
          │  DASHBOARD (Streamlit)  │
          │  dashboard/app.py       │
          │  Vista ejecutiva +      │
          │  operativa              │
          └─────────────────────────┘
```

## Orquestador

`src/pipeline.py` ejecuta las etapas en orden y **detiene ante el primer fallo**
(fail-fast):

```bash
python3 src/pipeline.py                # corre todo
python3 src/pipeline.py --etapa marts  # solo una etapa
python3 src/pipeline.py --desde staging --hasta validar
python3 src/pipeline.py --lista        # lista las etapas
```

Orden de ejecución: `generar → staging → marts → validar → analizar → modelos`.

## Tests

Suite de pytest (`tests/`). Se ejecuta con:

```bash
python3 -m pytest tests/ -v
```

| Archivo | Qué verifica |
|---|---|
| `test_staging.py` | Limpieza: nulos, duplicados, fechas, duración, tarifa, flags binarios |
| `test_marts.py` | Integridad referencial, unicidad de hechos, grano de agregados, consistencia |
| `test_validar.py` | El runner de calidad de datos da 0 fallidos |

Los tests usan **directorios temporales** y datasets sintéticos pequeños
(generados con el mismo `generar_datos.generar()`, semilla fija → reproducible).

## Validación de calidad de datos

`src/validar.py` ejecuta 12 checks (6 de staging + 6 de marts). Falla con
exit code != 0 si algún check crítico no pasa, por lo que puede correr como
**gate en CI** antes de publicar los marts.

## Programación (scheduler)

El pipeline es determinista y reproducible. Se puede programar de dos formas:

### 1. Local (cron)

```cron
# Correr el pipeline completo todos los días a las 06:00 (hora local)
0 6 * * * cd /ruta/al/repo && .venv/bin/python src/pipeline.py >> logs/pipeline.log 2>&1
```

### 2. CI/CD (GitHub Actions)

Ver `.github/workflows/pipeline.yml`. Corre el pipeline y los tests en cada
push y de forma programada, garantizando que los marts solo se publican si la
validación pasa.

## Estructura de archivos

```
rentacar-sjo-demand-intelligence/
├── data/
│   ├── raw/        # fuente (CSV sintético, generado)
│   ├── staging/    # staging.db (limpio, auditado)
│   ├── marts/      # marts.db (estrella + agregados)
│   └── processed/  # gráficos de salida
├── sql/
│   ├── schema_staging.sql   # esquema de staging + auditoría
│   └── schema_marts.sql     # dimensiones + hechos + agregados
├── src/
│   ├── config.py            # rutas y constantes compartidas
│   ├── generar_datos.py     # FUENTE
│   ├── staging.py           # STAGING
│   ├── marts.py             # MARTS
│   ├── validar.py           # VALIDACIÓN
│   ├── analisis.py          # KPIs
│   ├── modelo_no_show.py    # clasificación
│   ├── modelo_demanda.py    # pronóstico
│   └── pipeline.py          # ORQUESTADOR
├── tests/                   # pytest
├── dashboard/app.py         # Streamlit
├── docs/                    # esta documentación + caso de negocio
├── .github/workflows/       # CI/CD
├── requirements.txt
└── README.md
```

## Principios de diseño

1. **Separación de capas** — cada capa (fuente/staging/marts) tiene su propio
   script y su propio artefacto, con trazabilidad de origen.
2. **Grano explícito** — cada tabla declara su grano (`fact_reservas` = una fila
   por reserva; `mart_demanda_diaria` = una fila por fecha+categoría).
3. **Fail-fast** — la limpieza rechaza filas inválidas y el orquestador detiene
   todo si la validación falla.
4. **Reproducible** — semilla fija en el generador y tests deterministas.
5. **Testeado** — la integridad de cada capa se verifica con pytest.
