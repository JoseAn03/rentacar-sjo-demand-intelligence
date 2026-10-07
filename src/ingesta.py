#!/usr/bin/env python3
"""
Pipeline ETL — carga el CSV sintético a una base SQLite con modelo estrella.

Flujo: CSV (raw) -> limpieza -> dimensiones -> tabla de hechos -> SQLite.

Uso:  python3 src/ingesta.py
"""
import os
import sqlite3
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(BASE, "data", "raw", "reservas_sinteticas.csv")
DB = os.path.join(BASE, "data", "rentacar.db")
SCHEMA = os.path.join(BASE, "sql", "schema.sql")

ZONA_UBIC = {
    "SJO Aeropuerto": "Aeropuerto",
    "SJO Centro": "Centro",
    "Liberia": "Destino",
    "Quepos/Manuel Antonio": "Destino",
    "Tamarindo": "Destino",
    "Golfito": "Destino",
    "Nosara": "Destino",
}


def cargar_dimensiones(conn, df):
    """Inserta las dimensiones desde los valores distintos del CSV."""
    def upsert(table, cols, rows, key):
        cur = conn.cursor()
        for r in rows:
            cur.execute(
                f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['?']*len(cols))})",
                r,
            )
        conn.commit()

    # dim_vehiculo
    vehiculos = df[["clase", "categoria", "transmision"]].drop_duplicates()
    upsert("dim_vehiculo", ["clase", "categoria", "transmision"],
           [tuple(r) for r in vehiculos.itertuples(index=False)], "clase")

    # dim_ubicacion (recogida + entrega)
    ubics = pd.concat([
        df[["ubic_rec_cod", "ubic_rec"]].rename(columns={"ubic_rec_cod": "codigo", "ubic_rec": "nombre"}),
        df[["ubic_ent_cod", "ubic_ent"]].rename(columns={"ubic_ent_cod": "codigo", "ubic_ent": "nombre"}),
    ]).drop_duplicates()
    upsert("dim_ubicacion", ["codigo", "nombre", "zona"],
           [(c, n, ZONA_UBIC.get(n, "Otro")) for c, n in ubics.itertuples(index=False)], "codigo")

    # dim_tarifa
    tarifas = df[["codigo_tarifa", "tipo_tarifa"]].drop_duplicates()
    upsert("dim_tarifa", ["codigo", "tipo"],
           [tuple(r) for r in tarifas.itertuples(index=False)], "codigo")

    # dim_canal
    canales = df[["canal"]].drop_duplicates()
    upsert("dim_canal", ["nombre"], [(c,) for c in canales["canal"]], "nombre")

    # dim_cliente
    clientes = df[["tipo_cliente"]].drop_duplicates()
    upsert("dim_cliente", ["tipo"], [(c,) for c in clientes["tipo_cliente"]], "tipo")


def cargar_hechos(conn, df):
    """Inserta la tabla de hechos con las FK resueltas."""
    # Construir diccionarios de mapeo código -> id
    def map_id(table, key_col, id_col):
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
                r.id_reserva,
                str(r.fecha_recogida)[:10],
                m_veh[r.clase],
                m_ubic[r.ubic_rec_cod],
                m_ubic[r.ubic_ent_cod],
                m_tarifa[r.codigo_tarifa],
                m_canal[r.canal],
                m_cliente[r.tipo_cliente],
                str(r.fecha_reserva),
                str(r.fecha_recogida),
                str(r.fecha_entrega),
                int(r.anticipacion_dias),
                int(r.duracion_dias),
                float(r.tarifa_diaria),
                float(r.monto_total),
                int(r.tiene_vuelo),
                int(r.contactado),
                int(r.no_show),
            ),
        )
    conn.commit()


def cargar_dim_fecha(conn, df):
    """Puebla dim_fecha desde el rango de fechas del dataset."""
    fechas = pd.to_datetime(
        pd.concat([df["fecha_recogida"], df["fecha_entrega"], df["fecha_reserva"]])
    ).dt.normalize().unique()
    fechas = pd.Series(fechas).dropna().sort_values()

    import datetime
    feriados = {"01-01", "04-11", "05-01", "07-25", "08-02", "08-15", "09-15", "12-01", "12-25"}
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
                "Alta" if (d.month == 12 or d.month <= 4) else ("Baja" if d.month in (5,6,9,10,11) else "Media"),
                int(("%02d-%02d" % (d.month, d.day)) in feriados),
                0,
                int(d.weekday() >= 5),
            ),
        )
    conn.commit()


def main():
    if not os.path.exists(RAW):
        raise SystemExit("No existe el CSV. Ejecuta primero: python3 src/generar_datos.py")

    df = pd.read_csv(RAW, parse_dates=["fecha_reserva", "fecha_recogida", "fecha_entrega"])
    # Limpieza básica
    df = df.dropna(subset=["fecha_recogida", "fecha_entrega", "clase", "tarifa_diaria"])
    df = df[df["fecha_entrega"] >= df["fecha_recogida"]]

    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    with open(SCHEMA, encoding="utf-8") as f:
        conn.executescript(f.read())

    cargar_dim_fecha(conn, df)
    cargar_dimensiones(conn, df)
    cargar_hechos(conn, df)

    n = conn.execute("SELECT COUNT(*) FROM fact_reservas").fetchone()[0]
    conn.close()
    print(f"ETL completo: {n:,} filas en fact_reservas")
    print(f"Base de datos: {DB}")


if __name__ == "__main__":
    main()
