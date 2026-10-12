-- ============================================================
-- Capa MARTS — modelo dimensional (estrella) + agregados listos para
-- análisis y dashboard.
-- Motor: SQLite (Fase 1). Migrable a PostgreSQL sin cambios lógicos.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ---------- Dimensiones ----------
CREATE TABLE IF NOT EXISTS dim_fecha (
    fecha           DATE PRIMARY KEY,
    anio            INTEGER NOT NULL,
    mes             INTEGER NOT NULL,
    dia             INTEGER NOT NULL,
    dia_semana      INTEGER NOT NULL,      -- 0=lunes .. 6=domingo
    nombre_dia      TEXT    NOT NULL,
    semana           INTEGER NOT NULL,
    temporada       TEXT    NOT NULL,      -- Alta | Media | Baja
    es_feriado      INTEGER NOT NULL DEFAULT 0,
    es_semana_santa INTEGER NOT NULL DEFAULT 0,
    es_fin_semana   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dim_vehiculo (
    clase_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    clase       TEXT NOT NULL UNIQUE,      -- código ACRISS-like (CFAR, IFAR...)
    categoria   TEXT NOT NULL,             -- Compacto, SUV, Pickup...
    transmision TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_ubicacion (
    ubic_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo     TEXT NOT NULL UNIQUE,       -- SJOT71, LIRT71...
    nombre     TEXT NOT NULL,              -- SJO Aeropuerto, Liberia...
    zona       TEXT NOT NULL               -- Aeropuerto | Centro | Destino
);

CREATE TABLE IF NOT EXISTS dim_tarifa (
    tarifa_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo     TEXT NOT NULL UNIQUE,       -- CUST, EW4CR...
    tipo       TEXT NOT NULL               -- Turista | Corporativo | Promo
);

CREATE TABLE IF NOT EXISTS dim_canal (
    canal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre   TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_cliente (
    cliente_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo       TEXT NOT NULL UNIQUE        -- turista | local | corporativo
);

-- ---------- Tabla de hechos ----------
CREATE TABLE IF NOT EXISTS fact_reservas (
    id_reserva        TEXT PRIMARY KEY,
    fecha_key         DATE NOT NULL REFERENCES dim_fecha(fecha),
    clase_id          INTEGER NOT NULL REFERENCES dim_vehiculo(clase_id),
    ubic_rec_id       INTEGER NOT NULL REFERENCES dim_ubicacion(ubic_id),
    ubic_ent_id       INTEGER NOT NULL REFERENCES dim_ubicacion(ubic_id),
    tarifa_id         INTEGER NOT NULL REFERENCES dim_tarifa(tarifa_id),
    canal_id          INTEGER NOT NULL REFERENCES dim_canal(canal_id),
    cliente_id        INTEGER NOT NULL REFERENCES dim_cliente(cliente_id),
    fecha_reserva     DATETIME NOT NULL,
    fecha_recogida    DATETIME NOT NULL,
    fecha_entrega     DATETIME NOT NULL,
    anticipacion_dias INTEGER NOT NULL,
    duracion_dias     INTEGER NOT NULL,
    tarifa_diaria     REAL NOT NULL,
    monto_total       REAL NOT NULL,
    tiene_vuelo       INTEGER NOT NULL,
    contactado        INTEGER NOT NULL,
    no_show           INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_fecha   ON fact_reservas(fecha_key);
CREATE INDEX IF NOT EXISTS idx_fact_clase   ON fact_reservas(clase_id);
CREATE INDEX IF NOT EXISTS idx_fact_noshow  ON fact_reservas(no_show);
CREATE INDEX IF NOT EXISTS idx_fact_anticip ON fact_reservas(anticipacion_dias);

-- ---------- Agregados (marts analíticos materializados) ----------
-- Estos son los "one big table" / agregados que consume el dashboard y los
-- modelos, evitando recalcular joins en cada lectura.

-- Demanda diaria efectiva (llegadas) por día y categoría.
CREATE TABLE IF NOT EXISTS mart_demanda_diaria (
    fecha        DATE NOT NULL,
    categoria    TEXT NOT NULL,
    llegadas     INTEGER NOT NULL,
    no_shows     INTEGER NOT NULL,
    PRIMARY KEY (fecha, categoria)
);

-- Tasa de no-show por canal.
CREATE TABLE IF NOT EXISTS mart_noshow_canal (
    canal         TEXT PRIMARY KEY,
    reservas      INTEGER NOT NULL,
    no_shows      INTEGER NOT NULL,
    tasa_noshow   REAL NOT NULL
);

-- Ingreso efectivo por categoría de vehículo.
CREATE TABLE IF NOT EXISTS mart_ingreso_categoria (
    categoria         TEXT PRIMARY KEY,
    reservas          INTEGER NOT NULL,
    ingreso_promedio  REAL NOT NULL,
    ingreso_total     REAL NOT NULL
);
