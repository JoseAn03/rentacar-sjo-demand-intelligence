#!/usr/bin/env python3
"""
Análisis exploratorio + KPIs — responde "¿Dónde se pierde dinero?".

Lee de la capa MARTS (data/marts/marts.db) y genera resumen de KPIs en consola
y gráficos en data/processed/.

Uso:  python3 -m src.analisis   (o: python3 src/analisis.py)
"""
from __future__ import annotations

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from config import BASE, MARTS_DB, PROCESSED_DIR

DB = MARTS_DB
OUT = PROCESSED_DIR


def _q(conn, sql):
    return pd.read_sql_query(sql, conn)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    conn = sqlite3.connect(DB)

    print("=" * 60)
    print("KPIs DEL NEGOCIO")
    print("=" * 60)

    # 1. Volumen y no-show global
    total = _q(conn, "SELECT COUNT(*) n, SUM(no_show) ns FROM fact_reservas").iloc[0]
    print(f"\nReservas totales: {total['n']:,}")
    print(f"Tasa de no-show global: {100*total['ns']/total['n']:.1f}%")

    # 2. Ingreso perdido por no-show
    perdida = _q(conn, "SELECT ROUND(SUM(monto_total),0) v, COUNT(*) n FROM fact_reservas WHERE no_show=1").iloc[0]
    print(f"Ingreso perdido por no-show: ${perdida['v']:,.0f} ({perdida['n']:,} reservas)")

    # 3. No-show por canal (desde el agregado materializado)
    print("\n--- Tasa de no-show por canal ---")
    print(_q(conn, """
        SELECT canal, reservas, ROUND(tasa_noshow, 2) AS tasa
        FROM mart_noshow_canal ORDER BY tasa_noshow DESC
    """).to_string(index=False))

    # 4. No-show por anticipación
    print("\n--- No-show por anticipación ---")
    print(_q(conn, """
        SELECT CASE WHEN anticipacion_dias=0 THEN '0 (mismo día)'
                    WHEN anticipacion_dias<=3 THEN '1-3 días'
                    WHEN anticipacion_dias<=7 THEN '4-7 días'
                    WHEN anticipacion_dias<=14 THEN '8-14 días'
                    ELSE '15+ días' END anticipacion,
               COUNT(*) reservas, ROUND(100.0*SUM(no_show)/COUNT(*),1) tasa
        FROM fact_reservas GROUP BY anticipacion ORDER BY MIN(anticipacion_dias)
    """).to_string(index=False))

    # 5. Ingreso por categoría (desde el agregado materializado)
    print("\n--- Ingreso por categoría de vehículo ---")
    print(_q(conn, """
        SELECT categoria, reservas, ROUND(ingreso_total, 0) ingreso
        FROM mart_ingreso_categoria ORDER BY ingreso_total DESC
    """).to_string(index=False))

    # --- Gráficos ---
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    dem = _q(conn, """
        SELECT fecha dia, SUM(llegadas) llegadas FROM mart_demanda_diaria
        GROUP BY fecha ORDER BY fecha
    """)
    dem["dia"] = pd.to_datetime(dem["dia"])
    dem.set_index("dia")["llegadas"].resample("W").sum().plot(ax=axes[0, 0], title="Llegadas semanales")
    axes[0, 0].set_ylabel("reservas/semana")

    ns = _q(conn, """
        SELECT canal, tasa_noshow tasa FROM mart_noshow_canal ORDER BY tasa_noshow DESC
    """)
    ns.plot.bar(x="canal", y="tasa", ax=axes[0, 1], legend=False, title="No-show por canal")
    axes[0, 1].set_ylabel("% no-show")

    ing = _q(conn, """
        SELECT substr(fecha_key,1,7) mes, SUM(monto_total) ingreso
        FROM fact_reservas WHERE no_show=0 GROUP BY mes ORDER BY mes
    """)
    ing.plot(ax=axes[1, 0], x="mes", y="ingreso", legend=False, title="Ingreso mensual (efectivo)")
    axes[1, 0].tick_params(axis='x', rotation=45)

    dur = _q(conn, "SELECT duracion_dias d, COUNT(*) n FROM fact_reservas GROUP BY d ORDER BY d")
    dur.plot.bar(ax=axes[1, 1], x="d", y="n", legend=False, title="Distribución de duración")

    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "kpis.png"), dpi=100)
    print(f"\nGráficos guardados en {OUT}/kpis.png")
    conn.close()


if __name__ == "__main__":
    main()
