# Spike local de OmniRoute: diagnóstico histórico y cierre

Diagnóstico inicial: 25 de octubre de 2026. Cierre documental: 26 de octubre de 2026. Endpoint previsto y probado: `http://127.0.0.1:20128/v1`.

El bloqueo descrito en el corte inicial fue superado para la inferencia usando el catálogo del proveedor y un modelo concreto. La [validación final](registro-validacion-final-ia.md) confirma Google AI Studio y Gemini 3.5 Flash-Lite; las observaciones siguientes se conservan como historial.

## Corte inicial anterior a la validación real

La instalación existente informa versión **3.8.50**. Al comenzar no había servicio escuchando: `GET /v1/models` produjo `ConnectError`. Se realizó un arranque temporal de la instalación existente, con `HOSTNAME=127.0.0.1`, `PORT=20128` y su directorio de datos ya configurado. No se instalaron proveedores, no se modificó su configuración y no se extrajeron cookies, sesiones ni claves. El runtime cargó su propio archivo de entorno; NetAudit solo lee variables de su proceso.

| Comprobación real | Resultado |
|---|---|
| Salud `/api/health` | HTTP 200; aproximadamente 0,03 s |
| `GET /v1/models`, plazo inicial de 3 s | ReadTimeout |
| Catálogo, un nuevo intento con plazo de 20 s | ReadTimeout |
| Endpoint inexistente | HTTP 404; aproximadamente 0,75 s |
| Modelo deliberadamente inexistente en chat/completions | HTTP 400; 0,781 s |
| Solicitud de chat incompleta | HTTP 400; 0,024 s |
| Timeout controlado contra servidor local que acepta y no responde | Timeout observado; plazo 0,03 s |

**Modelo real utilizado: ninguno.** El catálogo no respondió, por lo que no fue posible enumerar modelos, confirmar Gemini 3.8 Flash ni elegir otro proveedor concreto. No se utilizó `auto`. No se ejecutaron las dos solicitudes de inferencia mínima/JSON contra un modelo supuesto. No hay latencia de inferencia exitosa que reportar.

El gateway responde HTTP, pero eso no demuestra disponibilidad del catálogo ni inferencia. No se identificó una causa raíz definitiva del bloqueo del catálogo. Se conserva este problema como limitación real, sin sustituirlo por resultados de mocks.

## Repetición manual

Iniciar la instalación ya existente, en una terminal separada:

```powershell
$env:HOSTNAME = '127.0.0.1'
$env:PORT = '20128'
$env:DATA_DIR = 'C:\Users\Gamer\Desktop\OmniRoute-Test\data'
& 'C:\Users\Gamer\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' '--env-file=C:\Users\Gamer\Desktop\OmniRoute-Test\data\.env' 'C:\Users\Gamer\Desktop\OmniRoute-Test\npm-global\node_modules\omniroute\dist\server-ws.mjs'
```

Ese comando logró abrir el listener local durante la revisión, pero no resolvió el timeout del catálogo. No recrear el archivo de entorno ni reemplazar la clave de cifrado de la instalación.

## Resolución comprobada

No se depende de `/v1/models`: la consulta administrativa específica del proveedor identificó
`gemini-3.5-flash-lite` y el registro instalado confirmó el ID `gemini/gemini-3.5-flash-lite`.
La llamada directa a Google devolvió `NETAUDIT_AI_OK`, HTTP 200, en 1,701 s. Con la
configuración final, OmniRoute lo devolvió en 1,731 s y las repeticiones secuenciales tardaron
1,877 / 1,560 / 1,557 s, todas por el proveedor oficial `gemini` y sin caché de respuesta.

El thinking predeterminado de la pasarela consumía el presupuesto de salida. Desactivarlo
mediante `reasoning_effort=none` produjo 400. La solución validada fue una regla de configuración
limitada a la clave NetAudit: presupuesto de razonamiento 128, conservando proveedor y modelo.
No se actualizó OmniRoute 3.8.50 ni se modificó código. No se ejecutaron otros modelos al
funcionar Gemini 3.5 Flash-Lite.

La explicación integral de 17 Findings y la conversación fueron reales, sus JSON pasaron
Pydantic y la caída controlada conservó el análisis. Véanse el [registro final](registro-validacion-final-ia.md)
y los [resultados sanitizados](evidencias-ai/validacion-gemini.json). La salud HTTP por sí sola
sigue sin demostrar inferencia. La prueba live optativa de pytest no fue necesaria para esta
validación y no se presenta como ejecutada.
