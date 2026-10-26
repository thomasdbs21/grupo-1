# Evidencias del baseline funcional de IA y Streamlit

Este directorio contiene instrucciones y un [registro sanitizado de resultados reales](validacion-gemini.json), sin credenciales ni capturas fabricadas. El estudiante debe tomar las capturas después de repetir cada acción. Usar una muestra sintética y ocultar terminales/ventanas con credenciales. No capturar archivos de entorno, tokens, cookies, sesiones, IP ni nombres reales del laboratorio.

| Nombre sugerido | Momento y contenido real que debe verse |
|---|---|
| `01-ui-inicial.png` | NetAudit abierto, modos Archivo/Dispositivo, sin datos de conexión ingresados. |
| `02-resultados-deterministas.png` | Después de analizar la muestra sintética: ID y contadores reales de evaluaciones. |
| `03-findings.png` | Uno o dos Findings abiertos, con rule_id, severidad, mensaje, recomendación y fragmento sintético. |
| `04-explicacion-ia.png` | Solo después de confirmar inferencia real: botón ejecutado y explicación obtenida del modelo configurado. Si no funciona, no crear esta captura como éxito. |
| `05-chat-ia.png` | Solo con el proveedor funcionando: pregunta sobre el mismo ID y respuesta real. |
| `06-ia-no-disponible.png` | Fallo real y controlado: aviso visible y Findings deterministas conservados. |
| `07-pytest-final.png` | Ejecución nueva de la suite normal: comando, resumen passed/failed/skipped/warnings y duración sin recortes engañosos. |
| `08-omniroute-modelo.png` | Solo si se resolvió el spike: modelo concreto disponible y resultado real de inferencia, ocultando claves y datos de cuentas. Un health HTTP 200 no basta. |

La [validación final](../registro-validacion-final-ia.md) ya confirmó explicación y conversación reales de Google AI Studio. En esa ejecución, Streamlit AppTest utilizó HTTP real y Gemini real, sin respuestas simuladas; la suite normal de pytest mantiene sus mocks y no consume el proveedor. Las evidencias Cisco del escenario integral fueron sintéticas y no se presentan como una nueva sesión SSH real.

## Capturas externas «ANTES»

El estudiante confirmó que las capturas actuales de Streamlit están guardadas externamente
y representan **«ANTES — MVP funcional previo al refinamiento visual»**. También confirmó
una captura de PowerShell con 800 tests pasando y una prueba correcta desde otro PC por Radmin.
No se proporcionaron aquí las rutas de esas imágenes ni se inspeccionaron en este cierre;
los nombres de la tabla son sugerencias, no archivos cuya existencia se dé por comprobada.
No se copian, reemplazan ni recrean esas capturas. El próximo incremento podrá compararlas
con el diseño posterior. El baseline de código es `3b7f916`, precedido por el merge `7c7d13b`.

El JSON versionado conserva solo resultados, métricas y verificaciones seleccionadas de la
validación del 25 de octubre. No incluye claves, IDs de credenciales, hosts de dispositivos,
configuraciones completas, prompts ni salidas SHOW originales.
