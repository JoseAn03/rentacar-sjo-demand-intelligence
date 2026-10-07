#!/usr/bin/env python3
"""
Análisis exploratorio + KPIs (Fase 2) — responde "¿Dónde se pierde dinero?".

Genera: resumen de KPIs en consola y gráficos en data/processed/.

Uso:  python3 src/analisis.py
"""
import os
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.join(os.path.dirname(__file__), "..")
DB = os.path.join(BASE, "data", "rentacar.db")
OUT = os.path.join(BASE, "data", "processed")
os.makedirs(OUT, exist_ok=True)

conn = sqlite3.connect(DB)

def q(sql):
    return pd.read_sql_query(sql, conn)

print("=" * 60)
print("KPIs DEL NEGOCIO")
print("=" * 60)

# 1. Volumen y no-show global
total = q("SELECT COUNT(*) n, SUM(no_show) ns FROM fact_reservas").iloc[0]
print(f"\nReservas totales: {total['n']:,}")
print(f"Tasa de no-show global: {100*total['ns']/total['n']:.1f}%")

# 2. Ingreso perdido por no-show
perdida = q("SELECT ROUND(SUM(monto_total),0) v, COUNT(*) n FROM fact_reservas WHERE no_show=1").iloc[0]
print(f"Ingreso perdido por no-show: ${perdida['v']:,.0f} ({perdida['n']:,} reservas)")

# 3. No-show por canal
print("\n--- Tasa de no-show por canal ---")
print(q("""
SELECT c.nombre canal, COUNT(*) reservas,
       ROUND(100.0*SUM(no_show)/COUNT(*),1) tasa
FROM fact_reservas f JOIN dim_canal c ON f.canal_id=c.canal_id
GROUP BY c.nombre ORDER BY tasa DESC
""").to_string(index=False))

# 4. No-show por anticipación
print("\n--- No-show por anticipación ---")
print(q("""
SELECT CASE WHEN anticipacion_dias=0 THEN '0 (mismo día)'
            WHEN anticipacion_dias<=3 THEN '1-3 días'
            WHEN anticipacion_dias<=7 THEN '4-7 días'
            WHEN anticipacion_dias<=14 THEN '8-14 días'
            ELSE '15+ días' END anticipacion,
       COUNT(*) reservas, ROUND(100.0*SUM(no_show)/COUNT(*),1) tasa
FROM fact_reservas GROUP BY anticipacion ORDER BY MIN(anticipacion_dias)
""").to_string(index=False))

# 5. Ingreso por categoría
print("\n--- Ingreso por categoría de vehículo ---")
print(q("""
SELECT v.categoria, COUNT(*) reservas, ROUND(SUM(f.monto_total),0) ingreso
FROM fact_reservas f JOIN dim_vehiculo v ON f.clase_id=v.clase_id
WHERE f.no_show=0 GROUP BY v.categoria ORDER BY ingreso DESC
""").to_string(index=False))

# --- Gráficos ---
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# Demanda diaria
dem = q("""
SELECT fecha_key dia, COUNT(*) llegadas FROM fact_reservas
WHERE no_show=0 GROUP BY fecha_key ORDER BY fecha_key
""")
dem["dia"] = pd.to_datetime(dem["dia"])
dem.set_index("dia")["llegadas"].resample("W").sum().plot(ax=axes[0,0], title="Llegadas semanales")
axes[0,0].set_ylabel("reservas/semana")

# No-show por canal
ns = q("""
SELECT c.nombre, 100.0*SUM(f.no_show)/COUNT(*) tasa
FROM fact_reservas f JOIN dim_canal c ON f.canal_id=c.canal_id
GROUP BY c.nombre ORDER BY tasa DESC
""")
ns.plot.bar(x="nombre", y="tasa", ax=axes[0,1], legend=False, title="No-show por canal")
axes[0,1].set_ylabel("% no-show")

# Ingreso por mes
ing = q("""
SELECT substr(fecha_key,1,7) mes, SUM(monto_total) ingreso
FROM fact_reservas WHERE no_show=0 GROUP BY mes ORDER BY mes
""")
ing.plot(ax=axes[1,0], x="mes", y="ingreso", legend=False, title="Ingreso mensual (efectivo)")
axes[1,0].tick_params(axis='x', rotation=45)

# Duración
dur = q("SELECT duracion_dias d, COUNT(*) n FROM fact_reservas GROUP BY d ORDER BY d")
dur.plot.bar(ax=axes[1,1], x="d", y="n", legend=False, title="Distribución de duración")

plt.tight_layout()
fig.savefig(os.path.join(OUT, "kpis.png"), dpi=100)
print(f"\nGráficos guardados en {OUT}/kpis.png")
conn.close()
