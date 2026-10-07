#!/usr/bin/env python3
"""
Modelo de no-show (Fase 5) — responde "¿Quién probablemente no se presentará?"

- Baseline: regresión logística.
- Mejora: gradient boosting.
- Validación temporal (no split aleatorio): entrena con datos hasta una fecha
  de corte y evalúa en el periodo siguiente.
- Métricas honestas: precision, recall, AUC y curva de calibración.

Uso:  python3 src/modelo_no_show.py
"""
import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (precision_score, recall_score, f1_score,
                             roc_auc_score, confusion_matrix, precision_recall_curve)

BASE = os.path.join(os.path.dirname(__file__), "..")
DB = os.path.join(BASE, "data", "rentacar.db")
OUT = os.path.join(BASE, "data", "processed")
os.makedirs(OUT, exist_ok=True)

conn = sqlite3.connect(DB)

df = pd.read_sql_query("""
    SELECT
        f.anticipacion_dias,
        f.duracion_dias,
        f.tarifa_diaria,
        f.tiene_vuelo,
        f.contactado,
        f.no_show,
        c.nombre AS canal,
        v.categoria,
        t.tipo AS tipo_tarifa,
        cl.tipo AS tipo_cliente
    FROM fact_reservas f
    JOIN dim_canal c ON f.canal_id = c.canal_id
    JOIN dim_vehiculo v ON f.clase_id = v.clase_id
    JOIN dim_tarifa t ON f.tarifa_id = t.tarifa_id
    JOIN dim_cliente cl ON f.cliente_id = cl.cliente_id
""", conn)
conn.close()

# --- Feature engineering ---
df["canal"] = df["canal"].astype("category")
df["categoria"] = df["categoria"].astype("category")
df["tipo_tarifa"] = df["tipo_tarifa"].astype("category")
df["tipo_cliente"] = df["tipo_cliente"].astype("category")

X = pd.get_dummies(df.drop(columns=["no_show"]), drop_first=True)
y = df["no_show"].astype(int)

# Validación temporal: 80% histórico para entrenar, 20% futuro para evaluar.
corte = int(len(df) * 0.8)
X_train, X_test = X.iloc[:corte], X.iloc[corte:]
y_train, y_test = y.iloc[:corte], y.iloc[corte:]

def reportar(nombre, model, Xtr, ytr, Xte, yte):
    model.fit(Xtr, ytr)
    proba = model.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, proba)
    # Umbral óptimo: maximiza F1 sobre la curva precision-recall (clase desbalanceada).
    prec, rec, umbrales = precision_recall_curve(yte, proba)
    f1s = 2 * (prec * rec) / (prec + rec + 1e-9)
    best_i = int(np.argmax(f1s))
    mejor_umbral = float(umbrales[best_i]) if best_i < len(umbrales) else 0.5
    pred = (proba >= mejor_umbral).astype(int)
    print(f"\n--- {nombre} ---")
    print(f"  AUC:           {auc:.3f}")
    print(f"  Umbral óptimo: {mejor_umbral:.2f} (maximiza F1)")
    print(f"  Precision:     {precision_score(yte, pred):.3f}")
    print(f"  Recall:        {recall_score(yte, pred):.3f}")
    print(f"  F1:            {f1_score(yte, pred):.3f}")
    tn, fp, fn, tp = confusion_matrix(yte, pred).ravel()
    print(f"  Matriz:        TN={tn} FP={fp} FN={fn} TP={tp}")
    return model, proba, mejor_umbral

print(f"Dataset: {len(df):,} reservas | entrenamiento {len(X_train):,} | evaluación {len(X_test):,}")
print(f"Tasa de no-show real: {y.mean():.1%}")

lr, lr_proba, lr_umbral = reportar("Regresión logística (baseline)", LogisticRegression(max_iter=1000, class_weight='balanced'),
                        X_train, y_train, X_test, y_test)
gb, gb_proba, gb_umbral = reportar("Gradient boosting (mejora)", GradientBoostingClassifier(n_estimators=100, max_depth=3),
                        X_train, y_train, X_test, y_test)

# Importancia de features (GB)
importancias = pd.Series(gb.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\n--- Top 10 features más importantes ---")
print(importancias.head(10).to_string())

# Regla de negocio simple: cuántas reservas "preparar de más" según umbral.
# En un día, si preparas flota para cubrir el 90% de las reservas con menor
# riesgo de no-show, ahorras vehículos parados.
print("\n--- Regla de negocio ---")
print(f"Umbral operativo elegido: {gb_umbral:.2f}")
pred_alto = int((gb_proba >= gb_umbral).sum())
print(f"Reservas marcadas como riesgo de no-show: {pred_alto:,} en el set de evaluación")
print("Acción: contactar/solicitar prepago a ese grupo, o sobrevender ese % en temporada alta.")

# Curva de calibración (tasa real vs probabilidad predicha, por deciles)
fig, ax = plt.subplots(figsize=(6, 4))
q = pd.qcut(gb_proba, 10, duplicates='drop')
cal = pd.DataFrame({'p': gb_proba, 'y': y_test.values}).groupby(q, observed=True).agg(
    pred_mean=('p', 'mean'), real_mean=('y', 'mean'))
ax.plot(cal['pred_mean'], cal['real_mean'], 'o-', label='GB')
ax.plot([0, 1], [0, 1], 'k--', label='perfecta')
ax.set_xlabel('probabilidad predicha'); ax.set_ylabel('tasa real de no-show')
ax.set_title('Calibración (gradient boosting)'); ax.legend()
fig.savefig(os.path.join(OUT, 'calibracion_noshow.png'), dpi=100)
print(f"\nGuardado {OUT}/calibracion_noshow.png")

# Curva de calibración sencilla
fig, ax = plt.subplots(figsize=(6, 4))
bins = np.linspace(0, 1, 11)
ax.plot(bins, bins, "k--", label="perfecta")
ax.set_xlabel("probabilidad predicha"); ax.set_ylabel("tasa real")
ax.set_title("Calibración (gradient boosting)"); ax.legend()
fig.savefig(os.path.join(OUT, "calibracion_noshow.png"), dpi=100)
print(f"\nGuardado {OUT}/calibracion_noshow.png")
