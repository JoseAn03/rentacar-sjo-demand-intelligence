#!/usr/bin/env python3
"""
Generador de datos sintéticos — Motor de demanda para rent-a-car (SJO).

Este script NO usa datos reales de la empresa. Replica la ESTRUCTURA y los
PATRONES observados en el manifiesto real de reservas (ResManifest) para
producir un dataset sintético realista y 100% público:

  - Clases de vehículo con códigos tipo ACRISS (CFAR, IFAR, SJAR, ...) y su
    distribución de frecuencia real.
  - Ubicaciones de recogida (SJO aeropuerto/centro) y entrega (incluye
    destinos turísticos de Costa Rica).
  - Códigos de tarifa reales (CUST, EW4CR, AW8CR, ...) correlacionados con
    la categoría del vehículo.
  - Canales de venta (Alamo, Enterprise, National, directo) con su mezcla.
  - Estacionalidad de Costa Rica: temporada alta (dic-abr), Semana Santa,
    feriados nacionales y patrón semanal.
  - Variable objetivo `no_show` (0/1) generada con reglas realistas según
    anticipación, tarifa, canal, contacto previo y tipo de cliente.

Salida: data/raw/reservas_sinteticas.csv  (formato limpio, listo para el ETL).

Uso:  python3 src/generar_datos.py
"""
import os
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261006)  # semilla fija -> reproducible

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Parámetros derivados de la estructura real del manifiesto
# ---------------------------------------------------------------------------
# Clase de vehículo (código ACRISS-like) -> (categoría, transmisión, peso relativo)
# Los pesos reflejan la frecuencia observada en el manifiesto real (580 filas).
CLASES = {
    "CJBR": ("Compacto", "Auto", 76),
    "IFAR": ("Intermedio", "Auto", 47),
    "CFAR": ("Compacto", "Auto", 44),
    "FFAR": ("Full Size", "Auto", 39),
    "SJAR": ("SUV", "Auto", 34),
    "PFBR": ("Pickup", "Auto 4x4", 31),
    "SFAR": ("SUV", "Auto", 31),
    "IFBR": ("Intermedio", "Auto 4x4", 29),
    "SFBR": ("SUV", "Auto 4x4", 29),
    "PFAR": ("Pickup", "Auto", 27),
    "FFBR": ("Full Size", "Auto 4x4", 24),
    "XFAR": ("Especial", "Auto", 20),
    "ICAR": ("Intermedio", "Auto", 17),
    "EFAR": ("Económico", "Auto", 15),
    "CCAR": ("Compacto", "Auto", 14),
    "FVAR": ("Van", "Auto", 10),
    "SFMR": ("SUV", "Manual", 10),
    "FPAR": ("Pickup", "Auto", 9),
    "FVBR": ("Van", "Auto 4x4", 7),
    "LFAR": ("Lujo", "Auto", 6),
    "XGAR": ("Especial", "Auto", 6),
    "CCMR": ("Compacto", "Manual", 5),
    "PGBR": ("Pickup", "Auto 4x4", 5),
    "FFMR": ("Full Size", "Manual", 5),
    "ECMR": ("Económico", "Manual", 4),
    "FCAR": ("Full Size", "Auto", 4),
    "IFMR": ("Intermedio", "Manual", 4),
    "ICMR": ("Intermedio", "Manual", 3),
    "ECAR": ("Económico", "Auto", 3),
    "IDAR": ("Intermedio", "Auto", 3),
    "EDAR": ("Económico", "Auto", 3),
}
CLASE_IDS = list(CLASES.keys())
CLASE_W = np.array([CLASES[c][2] for c in CLASE_IDS], dtype=float)

# Ubicaciones de recogida (código real -> descripción, peso)
UBIC_REC = {
    "SJOT71": ("SJO Aeropuerto", 216),
    "SJOT61": ("SJO Aeropuerto", 122),
    "SJOE71": ("SJO Centro", 106),
    "SJOT01": ("SJO Aeropuerto", 81),
    "SJOE01": ("SJO Centro", 41),
    "SJOC61": ("SJO Centro", 14),
}
UBIC_REC_IDS = list(UBIC_REC.keys())
UBIC_REC_W = np.array([UBIC_REC[c][1] for c in UBIC_REC_IDS], dtype=float)

# Ubicaciones de entrega: mayoría SJO, algunos destinos turísticos (one-way).
UBIC_ENT = {
    "SJOT71": ("SJO Aeropuerto", 184),
    "SJOT61": ("SJO Aeropuerto", 115),
    "SJOE71": ("SJO Centro", 86),
    "SJOT01": ("SJO Aeropuerto", 79),
    "SJOE01": ("SJO Centro", 34),
    "SJOC61": ("SJO Centro", 13),
    "LIRT71": ("Liberia", 12),
    "LIOS71": ("Liberia", 9),
    "XQPE71": ("Quepos/Manuel Antonio", 6),
    "TNON71": ("Tamarindo", 2),
    "GLFE71": ("Golfito", 2),
    "NOBR71": ("Nosara", 2),
}
UBIC_ENT_IDS = list(UBIC_ENT.keys())
UBIC_ENT_W = np.array([UBIC_ENT[c][1] for c in UBIC_ENT_IDS], dtype=float)

# Códigos de tarifa (real) -> (categoría, peso). CUST = corporativo/empleado.
TARIFAS = {
    "CUST": ("Corporativo", 76),
    "AW4CR": ("Turista", 35),
    "AW8CR": ("Turista", 29),
    "B12CR": ("Promo", 28),
    "EW4CR": ("Turista", 20),
    "AW1CR": ("Turista", 16),
    "EM8MCR": ("Promo", 15),
    "EW8CR": ("Turista", 14),
    "AW7CR": ("Turista", 14),
    "NCCP2022+": ("Corporativo", 13),
    "CRBCS2": ("Promo", 12),
    "EW7CR": ("Turista", 11),
    "AW3CR": ("Turista", 8),
    "PG7CR": ("Promo", 8),
    "EW6CR": ("Turista", 8),
    "AM8MCR": ("Promo", 8),
    "NW4CR": ("Turista", 7),
    "NW3CR": ("Turista", 7),
    "PR8CR": ("Promo", 7),
    "NW8CR": ("Turista", 6),
}
TARIFA_IDS = list(TARIFAS.keys())
TARIFA_W = np.array([TARIFAS[c][1] for c in TARIFA_IDS], dtype=float)

# Canal de venta (Reservado por) con su mezcla real aproximada.
CANALES = {
    "Alamo": 243,
    "Enterprise": 128,
    "National": 99,
    "Directo": 30,
}
CANAL_IDS = list(CANALES.keys())
CANAL_W = np.array([CANALES[c] for c in CANAL_IDS], dtype=float)

# Tarifa diaria base (USD) por categoría de vehículo -> rango realista.
TARIFA_BASE = {
    "Económico": (15, 30),
    "Compacto": (18, 45),
    "Intermedio": (25, 60),
    "Full Size": (35, 80),
    "SUV": (40, 90),
    "Pickup": (45, 100),
    "Van": (55, 108),
    "Especial": (30, 75),
    "Lujo": (60, 108),
}

# Feriados de Costa Rica (fechas fijas; Semana Santa se calcula aparte).
FERIADOS = [
    "01-01", "04-11", "05-01", "07-25", "08-02", "08-15", "09-15", "12-01", "12-25",
]

# ---------------------------------------------------------------------------
# 2. Utilidades de fecha
# ---------------------------------------------------------------------------
def es_feriado(d: pd.Timestamp) -> bool:
    return ("%02d-%02d" % (d.month, d.day)) in FERIADOS

def es_semana_santa(d: pd.Timestamp) -> bool:
    # Aproximación: Jueves y Viernes Santo (se calculan por año).
    import datetime
    year = d.year
    # Algoritmo de Butcher (Meeus/Jones/Butcher) para el domingo de Pascua.
    a = year % 19
    b = year // 100
    c = year % 100
    dd = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - dd - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = datetime.date(year, month, day)
    jueves = easter - datetime.timedelta(days=3)
    viernes = easter - datetime.timedelta(days=2)
    return d.date() in (jueves, viernes)

def temporada(d: pd.Timestamp) -> str:
    m = d.month
    if m == 12 or m <= 4:
        return "Alta"
    if m in (5, 6, 9, 10, 11):
        return "Baja"
    return "Media"

# ---------------------------------------------------------------------------
# 3. Generación de reservas
# ---------------------------------------------------------------------------
def generar(desde="2025-01-01", hasta="2026-09-30"):
    fechas = pd.date_range(desde, hasta, freq="D")
    filas = []

    for d in fechas:
        # Demanda base según temporada + fin de semana (aeropuerto: jue-dom).
        mult_temporada = {"Alta": 1.35, "Media": 1.0, "Baja": 0.72}[temporada(d)]
        mult_finde = 1.25 if d.weekday() >= 4 else 0.9  # jue..dom más demanda
        mult_semana_santa = 1.6 if es_semana_santa(d) else 1.0
        mult_feriado = 1.5 if es_feriado(d) else 1.0
        n_base = 82  # reservas/día promedio en temporada media
        n = int(RNG.poisson(n_base * mult_temporada * mult_finde * mult_semana_santa * mult_feriado))
        n = max(20, n)

        for _ in range(n):
            clase_id = RNG.choice(CLASE_IDS, p=CLASE_W / CLASE_W.sum())
            categoria, transmision, _ = CLASES[clase_id]

            # Fecha de recogida: hoy (o +1 día según anticipación)
            anticipacion = int(RNG.choice([0, 0, 0, 1, 1, 2, 2, 3, 4, 5, 7, 10, 14, 21, 30]))
            fecha_recogida = d + pd.Timedelta(days=int(RNG.choice([0, 1, 2])))
            fecha_reserva = fecha_recogida - pd.Timedelta(days=anticipacion)

            # Duración del alquiler (días), sesgada a corto (1-7) con cola larga.
            duracion = int(np.clip(RNG.geometric(0.35), 1, 21))

            fecha_entrega = fecha_recogida + pd.Timedelta(days=duracion)

            ubic_rec = RNG.choice(UBIC_REC_IDS, p=UBIC_REC_W / UBIC_REC_W.sum())
            # Entrega: 82% misma ubicación, 18% one-way a otro destino.
            if RNG.random() < 0.82:
                ubic_ent = ubic_rec
            else:
                ubic_ent = RNG.choice(UBIC_ENT_IDS, p=UBIC_ENT_W / UBIC_ENT_W.sum())

            canal = RNG.choice(CANAL_IDS, p=CANAL_W / CANAL_W.sum())

            tarifa_id = RNG.choice(TARIFA_IDS, p=TARIFA_W / TARIFA_W.sum())
            tarifa_cat = TARIFAS[tarifa_id][0]

            # Tipo de cliente según canal + tarifa
            if tarifa_cat == "Corporativo":
                tipo_cliente = RNG.choice(["corporativo", "corporativo", "local"], p=[0.7, 0.2, 0.1])
            elif tarifa_cat == "Promo":
                tipo_cliente = RNG.choice(["turista", "local", "corporativo"], p=[0.55, 0.3, 0.15])
            else:
                tipo_cliente = RNG.choice(["turista", "local", "corporativo"], p=[0.6, 0.28, 0.12])

            # Tarifa diaria base por categoría + ruido, ajustada por tipo.
            lo, hi = TARIFA_BASE[categoria]
            base = RNG.uniform(lo, hi)
            if tipo_cliente == "corporativo":
                base *= RNG.uniform(0.82, 0.95)
            elif tarifa_cat == "Promo":
                base *= RNG.uniform(0.7, 0.9)
            tarifa_diaria = round(base, 2)

            # Vuelo (asociado a aeropuerto y turista): ~28% tienen número de vuelo.
            tiene_vuelo = int(RNG.random() < 0.28)

            # Contacto previo al cliente (real: columna "Cliente Contactado").
            contactado = int(RNG.random() < 0.7)

            # ---- No-show (objetivo): probabilidad con reglas realistas ----
            p_noshow = 0.07  # base
            if anticipacion >= 14: p_noshow += 0.12       # reservas lejanas caen más
            elif anticipacion >= 7: p_noshow += 0.06
            if contactado == 0: p_noshow += 0.15          # sin confirmación
            if tarifa_cat == "Promo": p_noshow += 0.05    # tarifas baratas, menos compromiso
            if canal == "Directo": p_noshow -= 0.03
            if tipo_cliente == "turista" and tiene_vuelo: p_noshow -= 0.03
            if duracion >= 10: p_noshow += 0.04
            p_noshow = float(np.clip(p_noshow, 0.01, 0.6))
            no_show = int(RNG.random() < p_noshow)

            filas.append({
                "id_reserva": "SYN-%08d" % len(filas),
                "fecha_reserva": fecha_reserva,
                "fecha_recogida": fecha_recogida,
                "fecha_entrega": fecha_entrega,
                "anticipacion_dias": anticipacion,
                "duracion_dias": duracion,
                "clase": clase_id,
                "categoria": categoria,
                "transmision": transmision,
                "ubic_rec_cod": ubic_rec,
                "ubic_rec": UBIC_REC[ubic_rec][0],
                "ubic_ent_cod": ubic_ent,
                "ubic_ent": UBIC_ENT[ubic_ent][0],
                "codigo_tarifa": tarifa_id,
                "tipo_tarifa": tarifa_cat,
                "tarifa_diaria": tarifa_diaria,
                "canal": canal,
                "tipo_cliente": tipo_cliente,
                "tiene_vuelo": tiene_vuelo,
                "contactado": contactado,
                "no_show": no_show,
                "temporada": temporada(fecha_recogida),
                "es_feriado": int(es_feriado(fecha_recogida)),
                "es_semana_santa": int(es_semana_santa(fecha_recogida)),
            })

    df = pd.DataFrame(filas)
    # Monto total estimado (tarifa diaria * duración)
    df["monto_total"] = (df["tarifa_diaria"] * df["duracion_dias"]).round(2)
    # Ordenar cronológicamente por recogida
    df = df.sort_values(["fecha_recogida", "fecha_reserva"]).reset_index(drop=True)
    return df

if __name__ == "__main__":
    df = generar()
    out = os.path.join(OUT_DIR, "reservas_sinteticas.csv")
    df.to_csv(out, index=False)
    print(f"Generadas {len(df):,} reservas sintéticas")
    print(f"Tasa de no-show: {df['no_show'].mean():.1%}")
    print(f"Rango fechas: {df['fecha_recogida'].min().date()} -> {df['fecha_recogida'].max().date()}")
    print(f"Clases: {df['clase'].nunique()} | Categorías: {df['categoria'].nunique()}")
    print(f"Escrito en: {out}")
