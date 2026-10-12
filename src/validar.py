#!/usr/bin/env python3
"""
Capa de VALIDACIÓN — pruebas de calidad de datos.

Ejecuta checks de integridad sobre staging y marts. Cada check debe devolver
0 filas (o el valor esperado). Devuelve el resumen y falla (exit code != 0)
si algún check crítico falla.

Uso:  python3 -m src.validar   (o: python3 src/validar.py)
"""
from __future__ import annotations

import os
import sqlite3

from config import STAGING_DB, MARTS_DB

CHECKS_STAGING = [
    ("staging_nulos_obligatorios", """
        SELECT COUNT(*) FROM stg_reservas
        WHERE id_reserva IS NULL OR fecha_recogida IS NULL OR clase IS NULL
           OR tarifa_diaria IS NULL
    """, 0),
    ("staging_duplicados_id", """
        SELECT COUNT(*) FROM (
            SELECT id_reserva FROM stg_reservas GROUP BY id_reserva HAVING COUNT(*) > 1
        )
    """, 0),
    ("staging_entrega_antes_recogida", """
        SELECT COUNT(*) FROM stg_reservas WHERE fecha_entrega < fecha_recogida
    """, 0),
    ("staging_duracion_invalida", """
        SELECT COUNT(*) FROM stg_reservas WHERE duracion_dias <= 0 OR duracion_dias > 21
    """, 0),
    ("staging_tarifa_invalida", """
        SELECT COUNT(*) FROM stg_reservas WHERE tarifa_diaria <= 0 OR tarifa_diaria > 500
    """, 0),
    ("staging_flags_invalidos", """
        SELECT COUNT(*) FROM stg_reservas
        WHERE no_show NOT IN (0,1) OR tiene_vuelo NOT IN (0,1) OR contactado NOT IN (0,1)
    """, 0),
]

CHECKS_MARTS = [
    ("marts_hechos_sin_fecha", """
        SELECT COUNT(*) FROM fact_reservas f
        LEFT JOIN dim_fecha d ON f.fecha_key = d.fecha WHERE d.fecha IS NULL
    """, 0),
    ("marts_huerfano_clase", """
        SELECT COUNT(*) FROM fact_reservas f
        LEFT JOIN dim_vehiculo v ON f.clase_id = v.clase_id WHERE v.clase_id IS NULL
    """, 0),
    ("marts_huerfano_ubicacion", """
        SELECT COUNT(*) FROM fact_reservas f
        LEFT JOIN dim_ubicacion u ON f.ubic_rec_id = u.ubic_id WHERE u.ubic_id IS NULL
    """, 0),
    ("marts_huerfano_canal", """
        SELECT COUNT(*) FROM fact_reservas f
        LEFT JOIN dim_canal c ON f.canal_id = c.canal_id WHERE c.canal_id IS NULL
    """, 0),
    ("marts_duplicados_hechos", """
        SELECT COUNT(*) FROM (
            SELECT id_reserva FROM fact_reservas GROUP BY id_reserva HAVING COUNT(*) > 1
        )
    """, 0),
    ("marts_agregado_demanda_coherente", """
        SELECT COUNT(*) FROM (
            SELECT fecha, categoria FROM mart_demanda_diaria
            WHERE llegadas < 0 OR no_shows < 0
        )
    """, 0),
]


def _ejecutar(db: str, checks: list, nombre_capa: str) -> tuple[list[dict], int, int]:
    """Ejecuta checks y devuelve (resultados, pasados, fallidos)."""
    if not os.path.exists(db):
        return [{"check": f"[{nombre_capa}] DB no existe: {db}", "ok": False}], 0, 1

    conn = sqlite3.connect(db)
    resultados = []
    pasados = fallidos = 0
    for nombre, sql, esperado in checks:
        try:
            got = conn.execute(sql).fetchone()[0]
        except Exception as e:  # noqa: BLE001
            resultados.append({"check": nombre, "ok": False, "detalle": str(e)})
            fallidos += 1
            continue
        ok = got == esperado
        resultados.append({"check": nombre, "ok": ok, "obtenido": got, "esperado": esperado})
        pasados += ok
        fallidos += (not ok)
    conn.close()
    return resultados, pasados, fallidos


def run(staging_db: str = STAGING_DB, db: str = MARTS_DB) -> dict:
    """Ejecuta todas las validaciones y devuelve el resumen."""
    print("=" * 60)
    print("VALIDACIÓN DE CALIDAD DE DATOS")
    print("=" * 60)

    r_stg, p_stg, f_stg = _ejecutar(staging_db, CHECKS_STAGING, "staging")
    r_mart, p_mart, f_mart = _ejecutar(db, CHECKS_MARTS, "marts")

    for r in r_stg + r_mart:
        marca = "✓" if r["ok"] else "✗"
        detalle = f" (obtenido={r['obtenido']}, esperado={r['esperado']})" if not r["ok"] and "obtenido" in r else ""
        print(f"  {marca} {r['check']}{detalle}")

    total_p = p_stg + p_mart
    total_f = f_stg + f_mart
    print("-" * 60)
    print(f"Resultado: {total_p} ok | {total_f} fallidos")
    return {"pasados": total_p, "fallidos": total_f}


def main() -> int:
    res = run()
    return 1 if res["fallidos"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
