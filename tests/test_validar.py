"""
Tests de VALIDACIÓN de calidad de datos.

Ejecuta el runner de validación contra staging + marts temporales y verifica
que todos los checks pasan (0 fallidos).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

import generar_datos
import staging
import marts
import validar


@pytest.fixture(scope="module")
def dbs(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("validar")
    raw_csv = tmp / "reservas.csv"
    df = generar_datos.generar(desde="2025-01-01", hasta="2025-02-28")
    df.to_csv(raw_csv, index=False)

    stg_db = str(tmp / "staging.db")
    mrt_db = str(tmp / "marts.db")
    staging.run(raw_csv=str(raw_csv), db=stg_db)
    marts.run(staging_db=stg_db, db=mrt_db)
    return stg_db, mrt_db


def test_validacion_sin_fallos(dbs):
    stg_db, mrt_db = dbs
    res = validar.run(staging_db=stg_db, db=mrt_db)
    assert res["fallidos"] == 0, f"Hay {res['fallidos']} checks fallidos"
    assert res["pasados"] > 0
