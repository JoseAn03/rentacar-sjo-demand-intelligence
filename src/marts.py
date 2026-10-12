#!/usr/bin/env python3
"""
Capa MARTS — staging -> marts.

Construye el modelo dimensional (estrella) y los agregados analíticos
materializados a partir de la capa de staging.

Salida: `data/marts/marts.db` con:
  - Dimensiones: dim_fecha, dim_vehiculo, dim_ubicacion, dim_tarifa,
    dim_canal, dim_cliente.
  - Hechos: fact_reservas (grano = reserva).
  - Agregados: mart_demanda_diaria, mart_noshow_canal, mart_ingreso_categoria.

Uso:  python3 -m src.marts   (o: python3 src/marts.py)
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from config import (BASE, STAGING_DB, MARTS_DB, ZONA_UBIC, FERIADOS,
                    ensure_dirs, SQL_DIR)

SCHEMA_MARTS = os.path.join(SQL_DIR, "schema_marts.sql")


def _abrir_staging(db: str) -> pd.DataFrame:
    conn = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT * FROM stg_reservas", conn, parse_dates=[
            "fecha_reserva", "fecha_recogida", "fecha_entrega",
        ]
    )
    conn.close()
    return df


def _crear_dim_fecha(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    fechas = pd.to_datetime(
        pd.concat([df["fecha_recogida"], df["fecha_entrega"], df["fecha_reserva"]])
    ).dt.normalize().dropna().unique()
    fechas = pd.Series(fechas).sort_values()

    cur = conn.cursor()
    for f in fechas:
        d = pd.Timestamp(f)
        cur.execute(
            """INSERT OR IGNORE INTO dim_fecha
               (fecha, anio, mes, dia, dia_semana, nombre_dia, semana, temporada,
                es_feriado, es_semana_santa, es_fin_semana)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(d.date()),
                d.year, d.month, d.day, d.weekday(),
                d.day_name(), d.isocalendar().week,
                "Alta" if (d.month == 12 or d.month <= 4) else (
                    "Baja" if d.month in (5, 6, 9, 10, 11) else "Media"
                ),
                int(("%02d-%02d" % (d.month, d.day)) in FERIADOS),
                0,
                int(d.weekday() >= 5),
            ),
        )
    conn.commit()


def _upsert(conn: sqlite3.Connection, table: str, cols: list[str], rows: list) -> None:
    cur = conn.cursor()
    ph = ", ".join(["?"] * len(cols))
    cur.executemany(
        f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({ph})", rows
    )
    conn.commit()


def _crear_dimensiones(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    # dim_vehiculo
    v = df[["clase", "categoria", "transmision"]].drop_duplicates()
    _upsert(conn, "dim_vehiculo", ["clase", "categoria", "transmision"],
            [tuple(r) for r in v.itertuples(index=False)])

    # dim_ubicacion (recogida + entrega)
    u = pd.concat([
        df[["ubic_rec_cod", "ubic_rec"]].rename(columns={"ubic_rec_cod": "codigo", "ubic_rec": "nombre"}),
        df[["ubic_ent_cod", "ubic_ent"]].rename(columns={"ubic_ent_cod": "codigo", "ubic_ent": "nombre"}),
    ]).drop_duplicates()
    _upsert(conn, "dim_ubicacion", ["codigo", "nombre", "zona"],
            [(c, n, ZONA_UBIC.get(n, "Otro")) for c, n in u.itertuples(index=False)])

    # dim_tarifa
    t = df[["codigo_tarifa", "tipo_tarifa"]].drop_duplicates()
    _upsert(conn, "dim_tarifa", ["codigo", "tipo"],
            [tuple(r) for r in t.itertuples(index=False)])

    # dim_canal
    c = df[["canal"]].drop_duplicates()
    _upsert(conn, "dim_canal", ["nombre"], [(r,) for r in c["canal"]])

    # dim_cliente
    cl = df[["tipo_cliente"]].drop_duplicates()
    _upsert(conn, "dim_cliente", ["tipo"], [(r,) for r in cl["tipo_cliente"]])


def _crear_hechos(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    def map_id(table: str, key_col: str, id_col: str) -> dict:
        cur = conn.cursor()
        cur.execute(f"SELECT {key_col}, {id_col} FROM {table}")
        return dict(cur.fetchall())

    m_veh = map_id("dim_vehiculo", "clase", "clase_id")
    m_ubic = map_id("dim_ubicacion", "codigo", "ubic_id")
    m_tarifa = map_id("dim_tarifa", "codigo", "tarifa_id")
    m_canal = map_id("dim_canal", "nombre", "canal_id")
    m_cliente = map_id("dim_cliente", "tipo", "cliente_id")

    cur = conn.cursor()
    cur.execute("DELETE FROM fact_reservas")
    for r in df.itertuples(index=False):
        cur.execute(
            """INSERT OR REPLACE INTO fact_reservas
               (id_reserva, fecha_key, clase_id, ubic_rec_id, ubic_ent_id,
                tarifa_id, canal_id, cliente_id, fecha_reserva, fecha_recogida,
                fecha_entrega, anticipacion_dias, duracion_dias, tarifa_diaria,
                monto_total, tiene_vuelo, contactado, no_show)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                r.id_reserva, str(r.fecha_recogida)[:10],
                m_veh[r.clase], m_ubic[r.ubic_rec_cod], m_ubic[r.ubic_ent_cod],
                m_tarifa[r.codigo_tarifa], m_canal[r.canal], m_cliente[r.tipo_cliente],
                str(r.fecha_reserva), str(r.fecha_recogida), str(r.fecha_entrega),
                int(r.anticipacion_dias), int(r.duracion_dias),
                float(r.tarifa_diaria), float(r.monto_total),
                int(r.tiene_vuelo), int(r.contactado), int(r.no_show),
            ),
        )
    conn.commit()


def _crear_agregados(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # Demanda diaria efectiva por día y categoría.
    cur.execute("DELETE FROM mart_demanda_diaria")
    cur.execute("""
        INSERT INTO mart_demanda_diaria (fecha, categoria, llegadas, no_shows)
        SELECT f.fecha_key, v.categoria,
               SUM(CASE WHEN f.no_show = 0 THEN 1 ELSE 0 END) AS llegadas,
               SUM(f.no_show) AS no_shows
        FROM fact_reservas f
        JOIN dim_vehiculo v ON f.clase_id = v.clase_id
        GROUP BY f.fecha_key, v.categoria
    """)

    # No-show por canal.
    cur.execute("DELETE FROM mart_noshow_canal")
    cur.execute("""
        INSERT INTO mart_noshow_canal (canal, reservas, no_shows, tasa_noshow)
        SELECT c.nombre, COUNT(*), SUM(f.no_show),
               ROUND(100.0 * SUM(f.no_show) / COUNT(*), 4)
        FROM fact_reservas f
        JOIN dim_canal c ON f.canal_id = c.canal_id
        GROUP BY c.nombre
    """)

    # Ingreso por categoría (solo efectivas).
    cur.execute("DELETE FROM mart_ingreso_categoria")
    cur.execute("""
        INSERT INTO mart_ingreso_categoria (categoria, reservas, ingreso_promedio, ingreso_total)
        SELECT v.categoria, COUNT(*),
               ROUND(AVG(f.monto_total), 2), ROUND(SUM(f.monto_total), 2)
        FROM fact_reservas f
        JOIN dim_vehiculo v ON f.clase_id = v.clase_id
        WHERE f.no_show = 0
        GROUP BY v.categoria
    """)

    conn.commit()


def run(staging_db: str = STAGING_DB, db: str = MARTS_DB) -> dict:
    """Construye la capa de marts completa y devuelve un resumen."""
    if not os.path.exists(staging_db):
        raise SystemExit("No existe el staging. Ejecuta primero: python3 -m src.staging")

    df = _abrir_staging(staging_db)

    ensure_dirs()
    if os.path.exists(db):
        os.remove(db)

    conn = sqlite3.connect(db)
    with open(SCHEMA_MARTS, encoding="utf-8") as f:
        conn.executescript(f.read())

    _crear_dim_fecha(conn, df)
    _crear_dimensiones(conn, df)
    _crear_hechos(conn, df)
    _crear_agregados(conn)

    res = {
        "fact_reservas": conn.execute("SELECT COUNT(*) FROM fact_reservas").fetchone()[0],
        "dim_fecha": conn.execute("SELECT COUNT(*) FROM dim_fecha").fetchone()[0],
        "dim_vehiculo": conn.execute("SELECT COUNT(*) FROM dim_vehiculo").fetchone()[0],
        "dim_ubicacion": conn.execute("SELECT COUNT(*) FROM dim_ubicacion").fetchone()[0],
        "dim_tarifa": conn.execute("SELECT COUNT(*) FROM dim_tarifa").fetchone()[0],
        "dim_canal": conn.execute("SELECT COUNT(*) FROM dim_canal").fetchone()[0],
        "dim_cliente": conn.execute("SELECT COUNT(*) FROM dim_cliente").fetchone()[0],
        "db": db,
    }
    conn.close()

    print(f"[marts] fact_reservas={res['fact_reservas']:,} | "
          f"dims: fecha={res['dim_fecha']}, vehiculo={res['dim_vehiculo']}, "
          f"ubicacion={res['dim_ubicacion']}, tarifa={res['dim_tarifa']}, "
          f"canal={res['dim_canal']}, cliente={res['dim_cliente']} -> {db}")
    return res


if __name__ == "__main__":
    run()
