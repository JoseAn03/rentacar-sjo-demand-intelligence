#!/usr/bin/env python3
"""
ORQUESTADOR del pipeline.

Ejecuta las etapas en orden (fuente -> staging -> marts -> validar -> analizar)
y detiene la ejecución ante el primer fallo (fail-fast). Pensado para correr
tanto manual como en un scheduler (cron / GitHub Actions / Airflow).

Uso:
  python3 -m src.pipeline                # corre todo
  python3 -m src.pipeline --etapa marts  # corre solo una etapa
  python3 -m src.pipeline --lista        # lista las etapas
"""
from __future__ import annotations

import argparse
import sys

import config
import generar_datos
import staging
import marts
import validar


ETAPAS = {
    "generar": "Fuente: genera el dataset sintético",
    "staging": "Staging: limpia, tipa y valida la fuente",
    "marts": "Marts: construye modelo estrella + agregados",
    "validar": "Validación: checks de calidad de datos",
    "analizar": "Análisis: KPIs y gráficos",
    "modelos": "Modelos: no-show + pronóstico de demanda",
}

# Orden de ejecución (respeta dependencias).
ORDEN = ["generar", "staging", "marts", "validar", "analizar", "modelos"]


def _ejecutar_etapa(nombre: str) -> None:
    print(f"\n>>> ETAPA [{nombre}]: {ETAPAS[nombre]}")
    if nombre == "generar":
        generar_datos.main()
    elif nombre == "staging":
        staging.run()
    elif nombre == "marts":
        marts.run()
    elif nombre == "validar":
        res = validar.run()
        if res["fallidos"]:
            raise SystemExit("Validación fallida: abortando pipeline.")
    elif nombre == "analizar":
        import analisis
        analisis.main()
    elif nombre == "modelos":
        import modelo_no_show
        import modelo_demanda
        modelo_no_show.main()
        modelo_demanda.main()
    else:
        raise ValueError(f"Etapa desconocida: {nombre}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Orquestador del pipeline de datos")
    parser.add_argument("--etapa", choices=list(ETAPAS), help="Correr solo una etapa")
    parser.add_argument("--lista", action="store_true", help="Listar etapas y salir")
    parser.add_argument("--desde", help="Etapa inicial (corre desde ahí en adelante)")
    parser.add_argument("--hasta", help="Etapa final (inclusive)")
    args = parser.parse_args()

    if args.lista:
        for e in ORDEN:
            print(f"  {e:<9} {ETAPAS[e]}")
        return 0

    etapas = [args.etapa] if args.etapa else ORDEN
    if args.desde and not args.etapa:
        etapas = ORDEN[ORDEN.index(args.desde):]
    if args.hasta and not args.etapa:
        etapas = [e for e in etapas if ORDEN.index(e) <= ORDEN.index(args.hasta)]

    for e in etapas:
        _ejecutar_etapa(e)

    print("\n✓ Pipeline completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
