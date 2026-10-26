# Capturas manuales de evidencia

Este directorio contiene instrucciones, no imágenes generadas ni resultados simulados como prueba de proveedor real. El estudiante debe tomar las capturas después de repetir cada acción. Usar una muestra sintética y ocultar terminales/ventanas con credenciales. No capturar archivos de entorno, tokens, cookies, sesiones, IP ni nombres reales del laboratorio.

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

Antes de presentar 04, 05 u 08, completar el [spike](../registro-spike-omniroute.md). Si persiste el timeout de catálogo, registrar la limitación real en vez de fabricar esas imágenes. AppTest y MockTransport validan software; sus resultados no se presentan como respuestas reales de un proveedor ni de un router.
