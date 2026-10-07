# Caso de negocio (una página)

## Impacto estimado del no-show

Con datos sintéticos: **~57.000 reservas/año, tasa de no-show global ≈ 15%**.

- Si el ingreso promedio por reserva es ≈ **$135**, y el no-show deja el
  vehículo parado, el **ingreso perdido por no-show** ronda **$1.1M/año** en
  el dataset sintético.
- Un modelo de no-show que permita **contactar/confirmar al 30% de mayor
  riesgo** y recuperar siquiera el **20% de esos no-shows** ahorraría del orden
  de **$200.000/año** (supuesto: solo contactar, sin costo de prepago).

### Supuestos explícitos

| Supuesto | Valor | Nota |
|---|---|---|
| Ingreso promedio por reserva | $135 | derivado del dataset |
| Tasa de no-show global | 15% | varía por canal y anticipación |
| % de no-shows recuperables con contacto | 20% | conservador |
| Costo marginal de contactar | ~$0 | SMS/llamada automatizada |

Estos números son **ilustrativos** (datos sintéticos) y deben recalibrarse con
datos reales antes de presentarse como ahorro efectivo.

## Impacto operativo del pronóstico

- Conocer la demanda esperada de la semana reduce **vehículos parados** y
  **horas extra de mostrador** en horas pico.
- Un pronóstico con MAPE 24% (vs 42% del baseline) permite dimensionar flota
  con menos holgura y menor costo de oportunidad.

## Conclusión

El proyecto demuestra capacidad para convertir datos de reservas en decisiones:
medir (KPIs), anticipar (pronóstico) y actuar (no-show). Esa es la habilidad
que aporta un Data Analyst a la operación.
