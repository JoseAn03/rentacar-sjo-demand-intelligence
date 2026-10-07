# Relato de entrevista (2 minutos)

> "Cuéntame de un proyecto de datos del que estés orgulloso."

Construí un **motor de inteligencia de demanda para una rent-a-car en Costa
Rica**. El negocio perdía dinero por clientes que reservaban y no se
presentaban, y por no saber cuánta flota preparar cada semana.

**Lo que hice**: monté un pipeline completo — generé un dataset sintético
realista (respetando la confidencialidad de los datos reales), lo cargué a un
modelo dimensional en SQL, calculé KPIs de ocupación e ingreso, entrené un
modelo para pronosticar la demanda diaria (SARIMA, con validación temporal) y
un clasificador de no-show (logística + gradient boosting) que identifica qué
reservas tienen más riesgo de no llegar.

**Resultado**: el pronóstico redujo el error a la mitad frente a un baseline
simple, y el modelo de no-show mostró que el contacto previo al cliente y la
anticipación de la reserva son los mayores predictores — lo que se traduce en
una regla de negocio accionable: contactar al segmento de mayor riesgo antes
del día de recogida.

**Lo que aprendí**: la diferencia entre un modelo con buena métrica en papel y
uno que sirve en producción está en las preguntas de negocio correctas y en la
validación honesta (temporal, no aleatoria). Y que un proyecto terminado y bien
documentado vale más que uno enorme a medias.
