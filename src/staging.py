#!/usr/bin/env python3
"""
Capa STAGING — fuente -> staging.

Lee el CSV sintético (fuente), lo limpia, tipa y valida, y lo carga en una
base SQLite de staging (`data/staging/staging.db`) con trazabilidad de carga.

Reglas de limpieza (fail-fast, rechaza filas inválidas):
  - Nulos en campos obligatorios.
  - Entrega anterior a recogida.
  - Duración fuera de rango (<=0 o >21 días).
  - Tarifa diaria fuera de rango (<=0 o >500 USD).
  - Anticipación negativa.
  - Flags binarios fuera de {0,1}.

Uso:  python3 -m src.staging   (o: python3 src/staging.py)
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from config import (BASE, RAW_CSV, STAGING_DB, ensure_dirs,
                    DURACION_MAX_DIAS, TARIFA_MAX_USD)

SCHEMA_STAGING = os.path.join(BASE, "sql", "schema_staging.sql")


def _leer_fuente(ruta: str) -> pd.DataFrame:
    """Lee el CSV crudo con parseo de fechas."""
    return pd.read_csv(
        ruta,
        parse_dates=["fecha_reserva", "fecha_recogida", "fecha_entrega"],
    )


def limpiar(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Aplica reglas de limpieza y devuelve (limpio, rechazadas)."""
    antes = len(df)

    # 1) Nulos en campos obligatorios.
    obligatorios = [
        "id_reserva", "fecha_reserva", "fecha_recogida", "fecha_entrega",
        "clase", "categoria", "transmision", "ubic_rec_cod", "ubic_ent_cod",
        "codigo_tarifa", "tarifa_diaria", "canal", "tipo_cliente",
    ]
    df = df.dropna(subset=obligatorios)

    # 2) Coherencia de fechas: entrega >= recogida.
    df = df[df["fecha_entrega"] >= df["fecha_recogida"]]

    # 3) Duración en rango.
    df = df[(df["duracion_dias"] > 0) & (df["duracion_dias"] <= DURACION_MAX_DIAS)]

    # 4) Tarifa en rango.
    df = df[(df["tarifa_diaria"] > 0) & (df["tarifa_diaria"] <= TARIFA_MAX_USD)]

    # 5) Anticipación no negativa.
    df = df[df["anticipacion_dias"] >= 0]

    # 6) Flags binarios válidos.
    for flag in ("no_show", "tiene_vuelo", "contactado"):
        df = df[df[flag].isin([0, 1])]

    # 7) Duplicados de id_reserva (conserva el primero).
    df = df.drop_duplicates(subset="id_reserva", keep="first")

    rechazadas = antes - len(df)
    return df, rechazadas


def _cargar(df: pd.DataFrame, db: str) -> dict:
    """Carga el staging limpio y registra la auditoría de carga."""
    ensure_dirs()
    if os.path.exists(db):
        os.remove(db)

    conn = sqlite3.connect(db)
    with open(SCHEMA_STAGING, encoding="utf-8") as f:
        conn.executescript(f.read())

    # Registrar la carga.
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stg_carga (fuente, cargada_en, filas_leidas, filas_ok) VALUES (?,?,?,?)",
        (RAW_CSV, datetime.now(timezone.utc).isoformat(), len(df), len(df)),
    )
    carga_id = cur.lastrowid

    # Insertar filas de staging.
    filas = [
        (
            r.id_reserva, str(r.fecha_reserva), str(r.fecha_recogida),
            str(r.fecha_entrega), int(r.anticipacion_dias), int(r.duracion_dias),
            r.clase, r.categoria, r.transmision, r.ubic_rec_cod, r.ubic_rec,
            r.ubic_ent_cod, r.ubic_ent, r.codigo_tarifa, r.tipo_tarifa,
            float(r.tarifa_diaria), r.canal, r.tipo_cliente, int(r.tiene_vuelo),
            int(r.contactado), int(r.no_show), float(r.monto_total),
            r.temporada, int(r.es_feriado), int(r.es_semana_santa), carga_id,
        )
        for r in df.itertuples(index=False)
    ]
    cur.executemany(
        """INSERT INTO stg_reservas (
            id_reserva, fecha_reserva, fecha_recogida, fecha_entrega,
            anticipacion_dias, duracion_dias, clase, categoria, transmision,
            ubic_rec_cod, ubic_rec, ubic_ent_cod, ubic_ent, codigo_tarifa,
            tipo_tarifa, tarifa_diaria, canal, tipo_cliente, tiene_vuelo,
            contactado, no_show, monto_total, temporada, es_feriado,
            es_semana_santa, carga_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        filas,
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM stg_reservas").fetchone()[0]
    conn.close()
    return {"filas": n, "carga_id": carga_id, "db": db}


def run(raw_csv: str = RAW_CSV, db: str = STAGING_DB) -> dict:
    """Ejecuta la capa de staging completa y devuelve un resumen."""
    if not os.path.exists(raw_csv):
        raise SystemExit(
            "No existe el CSV fuente. Ejecuta primero: python3 -m src.generar_datos"
        )
    df = _leer_fuente(raw_csv)
    df, rechazadas = limpiar(df)
    res = _cargar(df, db)
    res["rechazadas"] = rechazadas
    print(f"[staging] {res['filas']:,} filas ok | {rechazadas:,} rechazadas -> {db}")
    return res


if __name__ == "__main__":
    run()
