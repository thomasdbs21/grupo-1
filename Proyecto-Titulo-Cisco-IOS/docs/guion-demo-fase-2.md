# Demo de NetAudit en cinco minutos

Usar exclusivamente muestras sintéticas. No mostrar credenciales, direcciones reales ni configuraciones del laboratorio. En esta rama local están integradas 21 reglas y ocho comandos; main conserva su estado independiente. La exposición debe distinguir código implementado, pruebas simuladas y validación real del proveedor.

## Preparación

Iniciar FastAPI y Streamlit con los comandos del [registro de integración](registro-integracion-ia.md). Usar `samples/evaluacion_2/escenario_inseguro.cfg`. Confirmar que la suite normal pase con `python -m pytest -q`. Para mostrar explicación y chat reales, usar la configuración ya validada de Google AI Studio y `gemini/gemini-3.5-flash-lite`, documentada en el [cierre](registro-validacion-final-ia.md), y comprobar su disponibilidad antes de exponer. No activar el test live sin esa verificación.

Si el gateway sigue fallando, presentar la demo determinista y el manejo de indisponibilidad. Aclarar que la inferencia fue validada anteriormente pero el proveedor no está disponible durante esa ejecución; no mostrar un fake como inferencia real.

| Tiempo | Acción y explicación oral |
|---|---|
| 0:00–0:30 | Abrir `http://127.0.0.1:8501`. «NetAudit audita configuraciones Cisco en modo de solo lectura. Las reglas detectan, la evidencia demuestra y la IA explica». |
| 0:30–1:20 | Elegir Analizar archivo, cargar la muestra sintética y analizar. Mostrar los contadores. Aclarar que archivo ejecuta 14 reglas de configuración; las 21 se usan en el análisis integral con evidencia operacional. |
| 1:20–2:00 | Abrir dos Findings: rule_id, severidad, mensaje, recomendación y evidencia mínima. Explicar que solo FAIL produce un Finding. |
| 2:00–2:50 | Pulsar el botón existente Explicar hallazgos con el proveedor validado. «El backend recupera Findings por su ID, elimina secretos y valida referencias. La IA no decide cumplimiento». Si falla, mostrar el aviso real y conservar los Findings a la vista. |
| 2:50–3:40 | Si IA está disponible, preguntar «¿Cuál es el hallazgo que debería revisar primero y por qué?». La pregunta usa el ID ya registrado, sin editar Findings. Si no está disponible, explicar esta limitación sin simular una respuesta. |
| 3:40–4:30 | Volver a los resultados deterministas y comparar sus estados, severidades y evidencia. Mostrar las pruebas de invariancia; la explicación es un objeto separado. |
| 4:30–5:00 | Mostrar el resumen real de pytest y el registro final: 3/3 pruebas, JSON Pydantic e invariantes preservados. Cerrar con límites: contexto en memoria, dependencia del proveedor y persistencia pendiente. |

## Fallo controlado opcional

Iniciar FastAPI con `NETAUDIT_AI_ENABLED=false`, o detener manualmente el gateway propio. Al pulsar la explicación debe aparecer: «La explicación mediante IA no está disponible. Los resultados deterministas del análisis siguen siendo válidos». No apagar servicios ajenos ni borrar configuración para provocar el fallo. No es necesario conectar un router para esta demo.

El modo Analizar dispositivo exige un laboratorio autorizado y credenciales introducidas por el estudiante. Su validación durante este incremento fue simulada: ocho consultas, 21 evaluaciones y registro de execution_id. No atribuir esos tests a una nueva sesión real.

## Baseline anterior al refinamiento visual

Las capturas actuales fueron guardadas externamente por el estudiante bajo el criterio
**«ANTES — MVP funcional previo al refinamiento visual»**. También reporta una captura
PowerShell con 800 pruebas aprobadas y una prueba correcta desde un segundo PC por Radmin.
Este cierre no modifica la UI, no reemplaza esas capturas ni atribuye a una captura no
inspeccionada una comprobación automatizada. La explicación integral validada utilizó
21 reglas, ocho evidencias sintéticas y 17 Findings; cargar solo el archivo en la UI
ejecuta 14 reglas y produce 12 Findings para esa muestra.
