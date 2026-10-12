"""
Tests de la capa de MARTS.

Verifican integridad referencial, unicidad de hechos, consistencia de los
agregados materializados y el grano de cada tabla.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

import generar_datos
import staging
import marts


@pytest.fixture(scope="module")
def marts_fixture(tmp_path_factory):
    """Construye staging + marts en un directorio temporal. Devuelve (db, n_staging)."""
    tmp = tmp_path_factory.mktemp("marts")
    raw_csv = tmp / "reservas.csv"
    df = generar_datos.generar(desde="2025-01-01", hasta="2025-03-31")
    df.to_csv(raw_csv, index=False)

    stg_db = str(tmp / "staging.db")
    mrt_db = str(tmp / "marts.db")
    res = staging.run(raw_csv=str(raw_csv), db=stg_db)
    marts.run(staging_db=stg_db, db=mrt_db)
    return mrt_db, res["filas"]


@pytest.fixture(scope="module")
def marts_db(marts_fixture):
    return marts_fixture[0]


@pytest.fixture(scope="module")
def n_staging(marts_fixture):
    return marts_fixture[1]


def _q(marts_db, sql):
    conn = sqlite3.connect(marts_db)
    try:
        return conn.execute(sql).fetchone()[0]
    finally:
        conn.close()


def test_hechos_no_vacios(marts_db):
    assert _q(marts_db, "SELECT COUNT(*) FROM fact_reservas") > 0


def test_hechos_unicos(marts_db):
    dup = _q(marts_db, """
        SELECT COUNT(*) FROM (
            SELECT id_reserva FROM fact_reservas GROUP BY id_reserva HAVING COUNT(*) > 1
        )
    """)
    assert dup == 0


def test_integridad_referencial(marts_db):
    """Ningún hecho puede quedar sin su dimensión."""
    huerfanos_clase = _q(marts_db, """
        SELECT COUNT(*) FROM fact_reservas f
        LEFT JOIN dim_vehiculo v ON f.clase_id = v.clase_id WHERE v.clase_id IS NULL
    """)
    huerfanos_fecha = _q(marts_db, """
        SELECT COUNT(*) FROM fact_reservas f
        LEFT JOIN dim_fecha d ON f.fecha_key = d.fecha WHERE d.fecha IS NULL
    """)
    huerfanos_canal = _q(marts_db, """
        SELECT COUNT(*) FROM fact_reservas f
        LEFT JOIN dim_canal c ON f.canal_id = c.canal_id WHERE c.canal_id IS NULL
    """)
    assert huerfanos_clase == 0
    assert huerfanos_fecha == 0
    assert huerfanos_canal == 0


def test_dimensiones_pobladas(marts_db):
    for dim in ("dim_fecha", "dim_vehiculo", "dim_ubicacion", "dim_tarifa",
                "dim_canal", "dim_cliente"):
        assert _q(marts_db, f"SELECT COUNT(*) FROM {dim}") > 0, dim


def test_agregado_demanda_grano(marts_db):
    """mart_demanda_diaria: una fila por (fecha, categoria)."""
    dup = _q(marts_db, """
        SELECT COUNT(*) FROM (
            SELECT fecha, categoria FROM mart_demanda_diaria
            GROUP BY fecha, categoria HAVING COUNT(*) > 1
        )
    """)
    assert dup == 0


def test_agregado_noshow_canal_consistente(marts_db):
    """La tasa de no-show materializada debe estar en [0,100]."""
    mal = _q(marts_db, """
        SELECT COUNT(*) FROM mart_noshow_canal
        WHERE tasa_noshow < 0 OR tasa_noshow > 100
    """)
    assert mal == 0


def test_agregado_ingreso_categoria_consistente(marts_db):
    """El ingreso materializado debe ser no negativo."""
    mal = _q(marts_db, """
        SELECT COUNT(*) FROM mart_ingreso_categoria WHERE ingreso_total < 0
    """)
    assert mal == 0


def test_hechos_igual_staging(marts_db, n_staging):
    """El conteo de hechos debe coincidir con el de staging (sin pérdida)."""
    n_hechos = _q(marts_db, "SELECT COUNT(*) FROM fact_reservas")
    assert n_hechos == n_staging
