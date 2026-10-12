# Arquitectura del proyecto

> El pipeline por capas (fuente → staging → marts → dashboard), los tests y la
> programación se documentan en [`pipeline.md`](pipeline.md). Este archivo
> describe el modelo dimensional y las decisiones técnicas.

## Modelo dimensional (estrella)

- **fact_reservas**: una fila por reserva (grano = reserva).
  - Medidas: `tarifa_diaria`, `monto_total`, `no_show`, `anticipacion_dias`,
    `duracion_dias`.
- **dim_fecha**: calendario con temporada, feriados, fin de semana.
- **dim_vehiculo**: clase (código ACRISS-like) → categoría y transmisión.
- **dim_ubicacion**: código de sucursal → nombre y zona (aeropuerto/centro/destino).
- **dim_tarifa**: código de tarifa → tipo (turista/corporativo/promo).
- **dim_canal**: canal de venta (Alamo, Enterprise, National, directo).
- **dim_cliente**: tipo de cliente (turista/local/corporativo).

## Decisiones técnicas

- **SQLite** para Fase 1 (cero configuración, migrable a PostgreSQL).
- **SARIMA** en lugar de Prophet para el pronóstico (sin dependencias pesadas;
  Prophet queda como opcional).
- **Validación temporal** en ambos modelos: nunca split aleatorio, porque es
  serie temporal.
