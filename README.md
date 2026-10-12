# 🚗 Motor de Inteligencia de Demanda y Operaciones — Rent-a-Car (SJO)

Proyecto de datos de extremo a extremo para una rent-a-car con operación en el
aeropuerto de San José (SJO), Costa Rica. Construido como carta de presentación
para roles de **Data Analyst / BI Analyst**.

> ⚠️ **Confidencialidad**: este repositorio usa datos **100% sintéticos**. La
> estructura, los códigos de clase de vehículo, las ubicaciones, los códigos de
> tarifa y los canales replican el patrón real del negocio, pero **no** contiene
> nombres, documentos, números de reserva ni placas reales. El dataset real
> jamás se publica.

---

## 1. El problema de negocio

La rent-a-car pierde dinero en tres frentes que un analista puede medir y
anticipar:

1. **¿Cuánta demanda habrá?** — Saber cuántas llegadas esperar por día y
   categoría permite dimensionar flota y personal.
2. **¿Quién no se presentará (no-show)?** — Un cliente que reserva y no llega
   deja el vehículo parado y pierde el ingreso.
3. **¿Dónde se pierde dinero?** — Utilización de flota, ingresos por reserva,
   cancelaciones tardías y horas pico de mostrador.

**Principio guía**: primero datos confiables, luego análisis, luego modelos.

## 2. Las tres preguntas y sus entregables

| Pregunta | Entregable | Técnica |
|---|---|---|
| ¿Cuánta demanda habrá? | Pronóstico de llegadas por día y categoría (temporada alta, feriados CR, Semana Santa) | Series de tiempo (SARIMA), validación temporal |
| ¿Quién no se presentará? | Probabilidad de no-show por reserva | Regresión logística + gradient boosting, métricas honestas |
| ¿Dónde se pierde dinero? | KPIs de ocupación, ingreso y no-show | SQL analítico + dashboard |

## 3. Arquitectura

El pipeline sigue una arquitectura en capas (**medallón**): fuente → staging →
marts → dashboard, con tests y programación. Diagrama completo en
[`docs/pipeline.md`](docs/pipeline.md).

```
FUENTE                 STAGING                 MARTS                   DASHBOARD
(data/raw)             (data/staging)          (data/marts)            (dashboard)
─────────              ─────────────           ───────────             ──────────
generar_datos.py  -->  staging.py        -->   marts.py          -->   app.py
CSV sintético          limpia + tipa +         modelo estrella +       Streamlit
~57k reservas          auditoría               agregados materializados
```

- **Fuente (raw)**: `src/generar_datos.py` produce el dataset sintético.
- **Staging**: `src/staging.py` limpia, tipa y audita la fuente (`staging.db`).
- **Marts**: `src/marts.py` construye el modelo dimensional y agregados (`marts.db`).
- **Validación**: `src/validar.py` ejecuta 12 checks de calidad (gate de CI).
- **Dashboard**: Streamlit con vista ejecutiva y operativa.
- **Orquestador**: `src/pipeline.py` encadena las etapas (fail-fast).
- **Tests**: suite de pytest en `tests/`.
- **Programación**: cron local + GitHub Actions (`.github/workflows/pipeline.yml`).

## 4. Estructura del repositorio

```
rentacar-sjo-demand-intelligence/
├── data/
│   ├── raw/          # fuente: CSV sintético (generado, no versionado)
│   ├── staging/      # staging.db (limpio, auditado)
│   ├── marts/        # marts.db (estrella + agregados)
│   └── processed/    # gráficos y salidas (generados)
├── sql/
│   ├── schema_staging.sql  # esquema de staging + auditoría
│   └── schema_marts.sql    # dimensiones + hechos + agregados
├── src/
│   ├── config.py            # rutas y constantes compartidas
│   ├── generar_datos.py     # FUENTE
│   ├── staging.py           # STAGING
│   ├── marts.py             # MARTS
│   ├── validar.py           # VALIDACIÓN
│   ├── analisis.py          # EDA + KPIs
│   ├── modelo_no_show.py    # clasificación de no-show
│   ├── modelo_demanda.py    # pronóstico de demanda
│   └── pipeline.py          # ORQUESTADOR (fail-fast)
├── tests/                   # pytest (staging, marts, validación)
├── dashboard/
│   └── app.py               # Streamlit (ejecutiva + operativa)
├── .github/workflows/       # CI/CD (pipeline + tests)
├── notebooks/               # exploración (opcional)
├── docs/                    # pipeline, arquitectura, caso de negocio, relato
├── requirements.txt
└── README.md
```

## 5. Cómo ejecutarlo

```bash
# 1. Entorno
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Pipeline completo (fuente -> staging -> marts -> validar)
python3 src/pipeline.py

# ...o por etapas:
python3 src/generar_datos.py   # fuente
python3 src/staging.py         # staging
python3 src/marts.py           # marts
python3 src/validar.py         # validación

# 3. Tests
python3 -m pytest tests/ -v

# 4. Análisis, modelos y dashboard
python3 src/analisis.py
python3 src/modelo_no_show.py
python3 src/modelo_demanda.py
streamlit run dashboard/app.py
```

## 6. Resultados resumidos

- **Demanda**: SARIMA reduce el error del baseline (MAE 11.9 vs 20.0
  llegadas/día; MAPE 24% vs 42%).
- **No-show**: AUC ≈ 0.69. Las variables más relevantes son el **contacto
  previo al cliente** y la **anticipación** de la reserva (consistente con la
  intuición de negocio).
- **KPIs**: tasa de no-show global ~15%, con diferencias por canal y por
  anticipación. El no-show representa un ingreso perdido medible en dólares.

### KPIs

![KPIs](data/processed/kpis.png)

### Pronóstico de demanda

![Pronóstico de demanda](data/processed/pronostico_demanda.png)

### Calibración del modelo de no-show

![Calibración no-show](data/processed/calibracion_noshow.png)

## 7. Limitaciones honestas

- Los datos son sintéticos: los patrones son realistas pero no sustituyen la
  calibración con datos reales.
- El pronóstico usa SARIMA sobre una sola serie agregada; una versión por
  categoría de vehículo mejoraría la utilidad operativa.
- El modelo de no-show tiene recall limitado a umbrales bajos; en producción
  conviene optimizar el punto de operación según el costo de un falso positivo
  vs. un falso negativo.

## 8. Siguientes pasos

- Pronóstico desagregado por categoría de vehículo.
- Incluir Semana Santa y feriados como regresores explícitos en el modelo.
- Migrar SQLite → PostgreSQL y añadir dbt para el modelo dimensional.
- Ampliar la suite de tests (tests de los modelos y del dashboard).

Ver [docs/pipeline.md](docs/pipeline.md) para el diagrama del pipeline, los
tests y la programación; y [docs/](docs/) para el caso de negocio, el relato de
entrevista y el diccionario de datos completo.
