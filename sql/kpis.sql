-- ============================================================
-- KPIs analíticos del negocio (Fase 2) — responde la pregunta 3:
-- "¿Dónde se pierde dinero?"
-- ============================================================

-- KPI 1: Ocupación/utilización de flota por día
SELECT
    fecha_key AS dia,
    COUNT(*) AS reservas,
    COUNT(DISTINCT clase_id) AS categorias_activas
FROM fact_reservas
WHERE no_show = 0
GROUP BY fecha_key
ORDER BY reservas DESC
LIMIT 20;

-- KPI 2: Tasa de no-show global y por canal
SELECT
    c.nombre AS canal,
    COUNT(*) AS reservas,
    ROUND(100.0 * SUM(no_show) / COUNT(*), 2) AS tasa_noshow_pct
FROM fact_reservas f
JOIN dim_canal c ON f.canal_id = c.canal_id
GROUP BY c.nombre
ORDER BY tasa_noshow_pct DESC;

-- KPI 3: Ingreso por reserva y por categoría (solo efectivas)
SELECT
    v.categoria,
    COUNT(*) AS reservas,
    ROUND(AVG(f.monto_total), 2) AS ingreso_promedio,
    ROUND(SUM(f.monto_total), 2) AS ingreso_total
FROM fact_reservas f
JOIN dim_vehiculo v ON f.clase_id = v.clase_id
WHERE f.no_show = 0
GROUP BY v.categoria
ORDER BY ingreso_total DESC;

-- KPI 4: Ingreso perdido por no-show (dinero que no se cobró)
SELECT
    ROUND(SUM(f.monto_total), 2) AS ingreso_perdido_noshow,
    COUNT(*) AS reservas_noshow
FROM fact_reservas f
WHERE f.no_show = 1;

-- KPI 5: Anticipación promedio y su relación con no-show
SELECT
    CASE
        WHEN anticipacion_dias = 0 THEN '0 (mismo día)'
        WHEN anticipacion_dias <= 3 THEN '1-3 días'
        WHEN anticipacion_dias <= 7 THEN '4-7 días'
        WHEN anticipacion_dias <= 14 THEN '8-14 días'
        ELSE '15+ días'
    END AS anticipacion,
    COUNT(*) AS reservas,
    ROUND(100.0 * SUM(no_show) / COUNT(*), 2) AS tasa_noshow_pct
FROM fact_reservas
GROUP BY anticipacion
ORDER BY MIN(anticipacion_dias);

-- KPI 6: Demanda por hora pico de mostrador (día de la semana)
SELECT
    df.nombre_dia,
    COUNT(*) AS llegadas,
    ROUND(100.0 * SUM(no_show) / COUNT(*), 2) AS tasa_noshow_pct
FROM fact_reservas f
JOIN dim_fecha df ON f.fecha_key = df.fecha
GROUP BY df.dia_semana, df.nombre_dia
ORDER BY df.dia_semana;
