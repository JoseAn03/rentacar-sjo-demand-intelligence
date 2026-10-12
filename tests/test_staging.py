"""
Tests de la capa de STAGING.

Verifican que la limpieza produce datos coherentes: sin nulos obligatorios,
sin duplicados, fechas coherentes, duraciones y tarifas en rango, y flags
binarios válidos.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

import staging


@pytest.fixture(scope="module")
def staging_df():
    """Genera un dataset sintético pequeño en memoria y lo limpia."""
    import generar_datos
    df = generar_datos.generar(desde="2025-01-01", hasta="2025-01-31")
    return df


@pytest.fixture(scope="module")
def limpio(staging_df):
    df, rechazadas = staging.limpiar(staging_df)
    return df


def test_limpieza_no_vacia(limpio):
    assert len(limpio) > 0


def test_sin_nulos_obligatorios(limpio):
    obligatorios = ["id_reserva", "fecha_recogida", "fecha_entrega", "clase", "tarifa_diaria"]
    assert limpio[obligatorios].isna().sum().sum() == 0


def test_sin_duplicados_id(limpio):
    assert limpio["id_reserva"].is_unique


def test_entrega_despues_recogida(limpio):
    assert (limpio["fecha_entrega"] >= limpio["fecha_recogida"]).all()


def test_duracion_en_rango(limpio):
    assert (limpio["duracion_dias"] > 0).all()
    assert (limpio["duracion_dias"] <= 21).all()


def test_tarifa_en_rango(limpio):
    assert (limpio["tarifa_diaria"] > 0).all()
    assert (limpio["tarifa_diaria"] <= 500).all()


def test_anticipacion_no_negativa(limpio):
    assert (limpio["anticipacion_dias"] >= 0).all()


def test_flags_binarios(limpio):
    for flag in ("no_show", "tiene_vuelo", "contactado"):
        assert limpio[flag].isin([0, 1]).all()


def test_rechazos_no_excesivos(staging_df):
    """La limpieza no debe descartar la mayoría de las filas."""
    df, rechazadas = staging.limpiar(staging_df)
    assert rechazadas / len(staging_df) < 0.05
