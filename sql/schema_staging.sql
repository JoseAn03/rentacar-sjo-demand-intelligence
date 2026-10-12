-- ============================================================
-- Capa STAGING — copia limpia, tipada y auditada de la fuente.
-- Motor: SQLite. Una sola tabla de staging + tabla de auditoría de carga.
-- ============================================================

PRAGMA foreign_keys = ON;

-- Registro de cada carga de staging (linaje y trazabilidad).
CREATE TABLE IF NOT EXISTS stg_carga (
    carga_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente        TEXT NOT NULL,           -- ruta/archivo origen
    cargada_en    TEXT NOT NULL,           -- timestamp ISO-8601
    filas_leidas  INTEGER NOT NULL,
    filas_ok      INTEGER NOT NULL,
    filas_rechazadas INTEGER NOT NULL DEFAULT 0
);

-- Datos limpios y tipados, grano = reserva.
-- Nota: staging conserva los campos crudos ya validados; los tipos son
-- explícitos para detectar errores temprano (fail-fast).
CREATE TABLE IF NOT EXISTS stg_reservas (
    id_reserva        TEXT PRIMARY KEY,
    fecha_reserva     TEXT NOT NULL,
    fecha_recogida    TEXT NOT NULL,
    fecha_entrega     TEXT NOT NULL,
    anticipacion_dias INTEGER NOT NULL,
    duracion_dias     INTEGER NOT NULL,
    clase             TEXT NOT NULL,
    categoria         TEXT NOT NULL,
    transmision       TEXT NOT NULL,
    ubic_rec_cod      TEXT NOT NULL,
    ubic_rec          TEXT NOT NULL,
    ubic_ent_cod      TEXT NOT NULL,
    ubic_ent          TEXT NOT NULL,
    codigo_tarifa     TEXT NOT NULL,
    tipo_tarifa       TEXT NOT NULL,
    tarifa_diaria     REAL NOT NULL,
    canal             TEXT NOT NULL,
    tipo_cliente      TEXT NOT NULL,
    tiene_vuelo       INTEGER NOT NULL,
    contactado        INTEGER NOT NULL,
    no_show           INTEGER NOT NULL,
    monto_total       REAL NOT NULL,
    temporada         TEXT NOT NULL,
    es_feriado        INTEGER NOT NULL,
    es_semana_santa   INTEGER NOT NULL,
    carga_id          INTEGER NOT NULL REFERENCES stg_carga(carga_id)
);

CREATE INDEX IF NOT EXISTS idx_stg_recogida ON stg_reservas(fecha_recogida);
CREATE INDEX IF NOT EXISTS idx_stg_clase    ON stg_reservas(clase);
CREATE INDEX IF NOT EXISTS idx_stg_noshow   ON stg_reservas(no_show);
