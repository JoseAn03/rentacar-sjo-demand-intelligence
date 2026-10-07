-- ============================================================
-- Validaciones de calidad de datos (Fase 1)
-- Cada consulta debe devolver 0 filas (o el valor esperado).
-- ============================================================

-- 1) Nulos en campos obligatorios
SELECT 'nulo_id_reserva' AS check_name, COUNT(*) AS n
FROM fact_reservas WHERE id_reserva IS NULL
UNION ALL SELECT 'nulo_fecha_recogida', COUNT(*) FROM fact_reservas WHERE fecha_recogida IS NULL
UNION ALL SELECT 'nulo_clase', COUNT(*) FROM fact_reservas WHERE clase_id IS NULL
UNION ALL SELECT 'nulo_tarifa_diaria', COUNT(*) FROM fact_reservas WHERE tarifa_diaria IS NULL;

-- 2) Duplicados por id de reserva
SELECT id_reserva, COUNT(*) AS n
FROM fact_reservas
GROUP BY id_reserva
HAVING COUNT(*) > 1;

-- 3) Rango de fechas coherente: entrega >= recogida
SELECT COUNT(*) AS entrega_antes_recogida
FROM fact_reservas
WHERE fecha_entrega < fecha_recogida;

-- 4) Duraciones fuera de rango (<=0 o >21 días)
SELECT COUNT(*) AS duracion_invalida
FROM fact_reservas
WHERE duracion_dias <= 0 OR duracion_dias > 21;

-- 5) Tarifas negativas o absurdas
SELECT COUNT(*) AS tarifa_invalida
FROM fact_reservas
WHERE tarifa_diaria < 0 OR tarifa_diaria > 500;

-- 6) Anticipación negativa (reserva después de recogida)
SELECT COUNT(*) AS anticipacion_negativa
FROM fact_reservas
WHERE anticipacion_dias < 0;

-- 7) Flags binarios fuera de {0,1}
SELECT COUNT(*) AS flag_invalido
FROM fact_reservas
WHERE no_show NOT IN (0,1) OR tiene_vuelo NOT IN (0,1) OR contactado NOT IN (0,1);

-- 8) Integridad referencial (hechos sin dimensión)
SELECT 'huerfano_clase' AS check_name, COUNT(*) AS n
FROM fact_reservas f LEFT JOIN dim_vehiculo v ON f.clase_id = v.clase_id
WHERE v.clase_id IS NULL
UNION ALL SELECT 'huerfano_ubicacion', COUNT(*) FROM fact_reservas f LEFT JOIN dim_ubicacion u ON f.ubic_rec_id = u.ubic_id WHERE u.ubic_id IS NULL
UNION ALL SELECT 'huerfano_canal', COUNT(*) FROM fact_reservas f LEFT JOIN dim_canal c ON f.canal_id = c.canal_id WHERE c.canal_id IS NULL;
