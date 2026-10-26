# Spike local de OmniRoute

Fecha de revisión: 25 de octubre de 2026. Endpoint previsto y probado: `http://127.0.0.1:20128/v1`.

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

Primero resolver `GET http://127.0.0.1:20128/v1/models`. Si requiere Bearer, usar únicamente una variable de entorno existente y no imprimirla. Elegir un ID concreto disponible y gratuito: preferir Gemini 3.8 Flash oficial/gratuito solo si realmente aparece; después otro modelo gratuito estable; usar un proveedor free/no-key como alternativa. No contratar servicios ni usar cuentas/sesiones web como sustituto.

Validar manualmente `POST /v1/chat/completions` con «Responde únicamente: NETAUDIT_AI_OK» y luego un JSON simple. Solo después configurar `NETAUDIT_AI_MODEL` y activar NetAudit. Mantener su clave, si hace falta, en `NETAUDIT_AI_API_KEY`, nunca en Git ni capturas. El test live es optativo y está fuera de la suite normal; ver el registro de integración.
