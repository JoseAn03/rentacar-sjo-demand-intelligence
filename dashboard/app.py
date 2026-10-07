#!/usr/bin/env python3
"""
Dashboard ejecutivo + operativo (Fase 3) — Streamlit.

Vista ejecutiva: KPIs, tendencia, no-show por canal, ingreso.
Vista operativa: demanda esperada de la semana, horas pico, alertas de no-show.

Uso:  streamlit run dashboard/app.py
"""
import os
import sqlite3
import pandas as pd
import streamlit as st

BASE = os.path.join(os.path.dirname(__file__), "..")
DB = os.path.join(BASE, "data", "rentacar.db")

st.set_page_config(page_title="Motor de Demanda SJO", layout="wide")
st.title("🚗 Motor de Inteligencia de Demanda — Rent-a-Car (SJO)")

@st.cache_data
def cargar():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("""
        SELECT f.*, v.categoria, v.transmision, c.nombre AS canal,
               t.tipo AS tipo_tarifa, cl.tipo AS tipo_cliente
        FROM fact_reservas f
        JOIN dim_vehiculo v ON f.clase_id = v.clase_id
        JOIN dim_canal c ON f.canal_id = c.canal_id
        JOIN dim_tarifa t ON f.tarifa_id = t.tarifa_id
        JOIN dim_cliente cl ON f.cliente_id = cl.cliente_id
    """, conn)
    conn.close()
    df["fecha_recogida"] = pd.to_datetime(df["fecha_recogida"])
    return df

df = cargar()

tab = st.sidebar.radio("Vista", ["📊 Ejecutiva", "🔧 Operativa"])

if tab == "📊 Ejecutiva":
    st.header("Vista Ejecutiva")
    c1, c2, c3, c4 = st.columns(4)
    total = len(df)
    noshow = df["no_show"].mean() * 100
    ingreso = df.loc[df["no_show"] == 0, "monto_total"].sum()
    perdida = df.loc[df["no_show"] == 1, "monto_total"].sum()
    c1.metric("Reservas totales", f"{total:,}")
    c2.metric("Tasa de no-show", f"{noshow:.1f}%")
    c3.metric("Ingreso efectivo", f"${ingreso:,.0f}")
    c4.metric("Perdido por no-show", f"${perdida:,.0f}")

    st.subheader("Ingreso mensual")
    df["mes"] = df["fecha_recogida"].dt.to_period("M").astype(str)
    st.bar_chart(df.loc[df["no_show"] == 0].groupby("mes")["monto_total"].sum())

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("No-show por canal")
        st.bar_chart(df.groupby("canal")["no_show"].mean() * 100)
    with col2:
        st.subheader("Ingreso por categoría")
        st.bar_chart(df.loc[df["no_show"] == 0].groupby("categoria")["monto_total"].sum())

else:
    st.header("Vista Operativa")
    hoy = df["fecha_recogida"].max().date()
    st.subheader(f"Demanda esperada — semana del {hoy}")
    # Última semana completa de datos como proxy de "esta semana".
    ultima = df[df["fecha_recogida"] >= pd.Timestamp(hoy) - pd.Timedelta(days=7)]
    sem = ultima.groupby(ultima["fecha_recogida"].dt.day_name()).agg(
        llegadas=("id_reserva", "count"), noshow=("no_show", "mean"))
    sem["noshow"] = sem["noshow"] * 100
    st.dataframe(sem)

    st.subheader("Alertas de no-show (mayor riesgo)")
    riesgo = df.groupby(["canal", "tipo_cliente"])["no_show"].mean().reset_index()
    riesgo = riesgo.sort_values("no_show", ascending=False)
    st.dataframe(riesgo.style.format({"no_show": "{:.1%}"}))

st.caption("Datos 100% sintéticos generados para demostración. No contienen información real de clientes.")
