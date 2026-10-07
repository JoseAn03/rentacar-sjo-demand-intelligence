#!/usr/bin/env python3
"""
Pronóstico de demanda (Fase 4) — responde "¿Cuánta demanda habrá?"

- Baseline ingenuo: promedio móvil de 7 días.
- Modelo: SARIMA (estacionalidad semanal) ajustado a llegadas diarias.
- Validación temporal: entrena en histórico, evalúa en el tramo futuro.
- Reporta MAE/MAPE contra el baseline.

Nota: Prophet es opcional (requirements.txt). Aquí se usa SARIMA de
statsmodels, que no requiere dependencias extra.

Uso:  python3 src/modelo_demanda.py
"""
import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

BASE = os.path.join(os.path.dirname(__file__), "..")
DB = os.path.join(BASE, "data", "rentacar.db")
OUT = os.path.join(BASE, "data", "processed")

conn = sqlite3.connect(DB)
dem = pd.read_sql_query("""
    SELECT fecha_key AS dia, COUNT(*) AS llegadas
    FROM fact_reservas
    WHERE no_show = 0
    GROUP BY fecha_key
    ORDER BY fecha_key
""", conn)
conn.close()

dem["dia"] = pd.to_datetime(dem["dia"])
serie = dem.set_index("dia")["llegadas"].resample("D").sum().fillna(0)
print(f"Serie diaria: {len(serie)} días | media {serie.mean():.0f} llegadas/día")

# Corte temporal: 80% entrenamiento, 20% evaluación.
corte = int(len(serie) * 0.8)
train, test = serie.iloc[:corte], serie.iloc[corte:]

# Baseline: promedio móvil 7 días.
def media_movil(s, ventana=7):
    return s.rolling(ventana, min_periods=1).mean().shift(1)

base_pred = media_movil(train).reindex(test.index).fillna(train.mean())

# SARIMA(1,0,1)(1,1,1,7) — estacionalidad semanal.
print("Ajustando SARIMA (puede tardar ~30-60s)...")
model = SARIMAX(train, order=(1, 0, 1), seasonal_order=(1, 1, 1, 7),
                enforce_stationarity=False, enforce_invertibility=False)
fit = model.fit(disp=False)
sarima_pred = fit.get_forecast(steps=len(test)).predicted_mean

def mape(real, pred):
    return float(np.mean(np.abs((real - pred) / real)) * 100)

def mae(real, pred):
    return float(np.mean(np.abs(real - pred)))

print("\n--- Resultados (periodo de evaluación) ---")
print(f"Baseline MAE:  {mae(test, base_pred):.1f} llegadas/día | MAPE {mape(test, base_pred):.1f}%")
print(f"SARIMA   MAE:  {mae(test, sarima_pred):.1f} llegadas/día | MAPE {mape(test, sarima_pred):.1f}%")

fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(test.index, test.values, label="real", color="black")
ax.plot(test.index, base_pred.values, label="baseline (MA7)", linestyle="--")
ax.plot(test.index, sarima_pred.values, label="SARIMA", linestyle="-.")
ax.set_title("Pronóstico de demanda diaria"); ax.legend()
fig.savefig(os.path.join(OUT, "pronostico_demanda.png"), dpi=100)
print(f"\nGuardado {OUT}/pronostico_demanda.png")
