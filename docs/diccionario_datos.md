# Diccionario de datos

Dataset sintético `data/raw/reservas_sinteticas.csv`. Una fila = una reserva.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `id_reserva` | string | Identificador sintético (NO real) | `SYN-00000001` |
| `fecha_reserva` | datetime | Cuándo se hizo la reserva | `2025-06-10 14:00` |
| `fecha_recogida` | datetime | Cuándo recoge el vehículo | `2025-06-15 12:00` |
| `fecha_entrega` | datetime | Cuándo lo devuelve | `2025-06-18 12:00` |
| `anticipacion_dias` | int | Días entre reserva y recogida | `5` |
| `duracion_dias` | int | Días de alquiler | `3` |
| `clase` | string | Código de clase (ACRISS-like) | `CFAR` |
| `categoria` | string | Categoría del vehículo | `Compacto` |
| `transmision` | string | Automático / manual | `Auto` |
| `ubic_rec_cod` | string | Código de sucursal de recogida | `SJOT71` |
| `ubic_rec` | string | Nombre de la sucursal | `SJO Aeropuerto` |
| `ubic_ent_cod` | string | Código de sucursal de entrega | `LIRT71` |
| `ubic_ent` | string | Nombre de la sucursal | `Liberia` |
| `codigo_tarifa` | string | Código de tarifa | `EW4CR` |
| `tipo_tarifa` | string | Turista / Corporativo / Promo | `Turista` |
| `tarifa_diaria` | float | Precio por día (USD) | `28.00` |
| `monto_total` | float | tarifa_diaria × duración | `84.00` |
| `canal` | string | Canal de venta | `Alamo` |
| `tipo_cliente` | string | turista / local / corporativo | `turista` |
| `tiene_vuelo` | int | Tiene número de vuelo asociado | `1` |
| `contactado` | int | Cliente contactado previamente | `0` |
| `no_show` | int | **Objetivo**: no se presentó | `0` |
| `temporada` | string | Alta / Media / Baja | `Baja` |
| `es_feriado` | int | La recogida cae en feriado CR | `0` |
| `es_semana_santa` | int | Cae en Semana Santa | `0` |

## Campos sensibles excluidos del dataset real

En el manifiesto real existen campos que **nunca** se publican ni se replican:

- `Nombre` del cliente.
- `N.º reserva` real.
- `N.º unidad` (placa / identificación del vehículo).
- `N.º de vuelo` real.
- `Agencia de recom.` con nombres de terceros.

En su lugar se usan identificadores sintéticos y valores categóricos
anonimizados.
