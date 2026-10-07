# Problema de negocio y las 3 preguntas

## Contexto

Una rent-a-car con operación principal en el aeropuerto internacional de San
José (SJO) y sucursales en centros turísticos de Costa Rica necesita convertir
sus datos de reservas en decisiones: cuánta flota preparar, qué reservas tienen
riesgo de no presentarse y dónde se está perdiendo dinero.

## Las tres preguntas

### 1. ¿Cuánta demanda habrá?

**Por qué importa**: preparar vehículos y personal de mostrador de más cuesta
dinero; de menos, pierde clientes y reputación.

**Entrega**: pronóstico de llegadas por día (y por categoría de vehículo) que
capture la temporada alta (dic–abr), los feriados de Costa Rica y la Semana
Santa.

### 2. ¿Quién probablemente no se presentará (no-show)?

**Por qué importa**: un cliente que reserva y no llega deja el auto parado. Si
sabes de antemano quién es riesgo, puedes contactarlo, pedir prepago o
sobrevender en temporada alta.

**Entrega**: probabilidad de no-show por reserva según canal, anticipación,
duración, tarifa y tipo de cliente.

### 3. ¿Dónde se pierde dinero?

**Por qué importa**: no puedes mejorar lo que no mides.

**Entrega**: KPIs de ocupación/utilización, ingreso por reserva, upgrades,
cancelaciones tardías y horas pico de mostrador.

## Alcance (qué es y qué no es)

- **Es**: un pipeline reproducible de principio a fin, con datos sintéticos,
  modelo dimensional, KPIs, modelos y dashboard.
- **No es**: una réplica exacta del sistema de la empresa ni un producto en
  producción. Es una demostración de capacidad analítica de extremo a extremo.
