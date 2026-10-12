#!/usr/bin/env python3
"""
Pronóstico de demanda — responde "¿Cuánta demanda habrá?".

Lee de la capa MARTS. Compara un baseline (media móvil 7 días) contra SARIMA
con validación temporal y reporta MAE/MAPE.

Uso:  python3 -m src.modelo_demanda   (o: python3 src/modelo_demanda.py)
"""
from __future__ import annotations

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from config import MARTS_DB, PROCESSED_DIR

DB = MARTS_DB
OUT = PROCESSED_DIR


def _mae(real, pred):
    return float(np.mean(np.abs(real - pred)))


def _mape(real, pred):
    return float(np.mean(np.abs((real - pred) / real)) * 100)


def _media_movil(s, ventana=7):
    return s.rolling(ventana, min_periods=1).mean().shift(1)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    conn = sqlite3.connect(DB)
    dem = pd.read_sql_query("""
        SELECT fecha AS dia, SUM(llegadas) AS llegadas
        FROM mart_demanda_diaria
        GROUP BY fecha ORDER BY fecha
    """, conn)
    conn.close()

    dem["dia"] = pd.to_datetime(dem["dia"])
    serie = dem.set_index("dia")["llegadas"].resample("D").sum().fillna(0)
    print(f"Serie diaria: {len(serie)} días | media {serie.mean():.0f} llegadas/día")

    corte = int(len(serie) * 0.8)
    train, test = serie.iloc[:corte], serie.iloc[corte:]

    base_pred = _media_movil(train).reindex(test.index).fillna(train.mean())

    print("Ajustando SARIMA (puede tardar ~30-60s)...")
    model = SARIMAX(train, order=(1, 0, 1), seasonal_order=(1, 1, 1, 7),
                    enforce_stationarity=False, enforce_invertibility=False)
    fit = model.fit(disp=False)
    sarima_pred = fit.get_forecast(steps=len(test)).predicted_mean

    print("\n--- Resultados (periodo de evaluación) ---")
    print(f"Baseline MAE:  {_mae(test, base_pred):.1f} llegadas/día | MAPE {_mape(test, base_pred):.1f}%")
    print(f"SARIMA   MAE:  {_mae(test, sarima_pred):.1f} llegadas/día | MAPE {_mape(test, sarima_pred):.1f}%")

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(test.index, test.values, label="real", color="black")
    ax.plot(test.index, base_pred.values, label="baseline (MA7)", linestyle="--")
    ax.plot(test.index, sarima_pred.values, label="SARIMA", linestyle="-.")
    ax.set_title("Pronóstico de demanda diaria"); ax.legend()
    fig.savefig(os.path.join(OUT, "pronostico_demanda.png"), dpi=100)
    print(f"\nGuardado {OUT}/pronostico_demanda.png")


if __name__ == "__main__":
    main()
