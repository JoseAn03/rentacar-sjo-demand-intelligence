"""
Configuración central del pipeline.

Define rutas, constantes de negocio y convenciones compartidas por todas las
capas (fuente -> staging -> marts -> dashboard). Las rutas se pueden inyectar
en las funciones para permitir tests con directorios temporales.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Rutas (relativas a la raíz del repositorio)
# ---------------------------------------------------------------------------
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(BASE, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
STAGING_DIR = os.path.join(DATA_DIR, "staging")
MARTS_DIR = os.path.join(DATA_DIR, "marts")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
SQL_DIR = os.path.join(BASE, "sql")

RAW_CSV = os.path.join(RAW_DIR, "reservas_sinteticas.csv")
STAGING_DB = os.path.join(STAGING_DIR, "staging.db")
MARTS_DB = os.path.join(MARTS_DIR, "marts.db")

# ---------------------------------------------------------------------------
# Convenciones de negocio
# ---------------------------------------------------------------------------
# Zona por ubicación (para enriquecer la dimensión de ubicación).
ZONA_UBIC = {
    "SJO Aeropuerto": "Aeropuerto",
    "SJO Centro": "Centro",
    "Liberia": "Destino",
    "Quepos/Manuel Antonio": "Destino",
    "Tamarindo": "Destino",
    "Golfito": "Destino",
    "Nosara": "Destino",
}

# Feriados de Costa Rica (fechas fijas; Semana Santa se calcula aparte).
FERIADOS = {
    "01-01", "04-11", "05-01", "07-25",
    "08-02", "08-15", "09-15", "12-01", "12-25",
}

# Reglas de rango para validaciones de calidad de datos.
DURACION_MAX_DIAS = 21
TARIFA_MAX_USD = 500


def ensure_dirs() -> None:
    """Crea los directorios de salida si no existen."""
    for d in (RAW_DIR, STAGING_DIR, MARTS_DIR, PROCESSED_DIR):
        os.makedirs(d, exist_ok=True)
