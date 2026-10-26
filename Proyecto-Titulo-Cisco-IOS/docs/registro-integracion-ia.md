# Integración local de la explicación IA y la interfaz

Implementación: 25 de octubre de 2026. Cierre documental: 26 de octubre de 2026. Rama: `feature/ai-explainer-ui`. Este trabajo es local y no cambia el estado de main.

La inferencia real, conversación y resiliencia ya están validadas; ver el
[registro final del baseline](registro-validacion-final-ia.md) y la
[evidencia sanitizada](evidencias-ai/validacion-gemini.json). El MVP Streamlit conserva su diseño básico.

## Objetivo y base verificada

Se integró `feature/evaluacion-2-validacion` (`d3d05ca`) en una rama creada desde main actualizado (`2531791`). El merge fue automático, sin conflictos, y conservó la estructura y los documentos recientes de main. La rama original de Evaluación 2 no se modificó.

Antes del merge: **314 passed, 1 warning in 11.89s**. Después del merge y antes de IA/UI: **703 passed, 1 warning in 9.05s**. El catálogo integral mantiene **21 reglas: 14 de configuración y 7 operacionales**, con **8 comandos autorizados**. El análisis de archivo ejecuta las 14 reglas de configuración; las siete operacionales requieren evidencia adicional.

## Arquitectura y flujo

```text
Archivo o recopilación SSH read-only existente
  -> parsing y motor determinista
  -> evaluaciones inmutables -> solo FAIL produce Finding
  -> respuesta determinista existente
  -> snapshot separado y sanitizado, asociado a analysis_id/execution_id

Streamlit -> FastAPI -> repositorio temporal de contexto
                    -> servicio explicativo -> cliente HTTP -> OmniRoute
                    <- contrato JSON validado y referencias verificadas
```

La UI solo conoce FastAPI. El paquete `ios_auditor.ai` no importa Netmiko, collectors ni API. Recibe exclusivamente Findings de dominio construidos por el backend. No puede abrir SSH, ejecutar herramientas, aplicar configuraciones o cambiar estado, severidad, evidencia o Findings. El repositorio de IA conserva hasta 100 snapshots inmutables en memoria, compartidos entre archivos y dispositivos; los más antiguos se expulsan. No hay persistencia relacional nueva ni historial después de reiniciar.

Los análisis de archivo conservan su analysis_id; los de dispositivo usan execution_id. La UI envía solo el identificador y una pregunta opcional de hasta 500 caracteres. No acepta Findings editables. Un error al registrar el snapshot opcional se registra con un mensaje estático y no invalida el análisis determinista; si falta el contexto, la explicación devuelve 404.

## Información que recibe el modelo

Recibe rule_id como referencia, nombre de regla, severidad técnica ya fijada como dato de entrada, mensaje y recomendación del motor, fragmentos mínimos sanitizados y una pregunta sanitizada. El prompt está versionado como `netaudit-explainer-1`. Tanto evidencia como pregunta están en un objeto JSON `UNTRUSTED_DATA`; el sistema ordena ignorar instrucciones incrustadas allí.

No recibe contraseñas ni usuario SSH, host/IP del dispositivo, objetos de conexión, configuraciones completas, raw show outputs completos, archivos de sesión, cookies ni claves de API. No recibe el repositorio determinista ni funciones para modificarlo. Las claves necesarias para autenticar con el gateway van solo en el encabezado HTTP y no forman parte del prompt.

## Sanitización y límites

La redacción ocurre antes de truncar: enable secret/password, username secret/password, comunidades y usuarios SNMP, contraseñas de vecinos, crypto isakmp key, claves de autenticación/NTP/OSPF, key 7, key-string, RADIUS/TACACS, claves privadas PEM, claves SSH, tokens y asignaciones reconocibles de secretos se sustituyen por `<REDACTED>`. Se normaliza Unicode y se eliminan controles; también se redactan IP, hostname explícito y serial reconocible.

Por Finding se conservan como máximo dos evidencias de 500 caracteres. Se limita a 32 Findings y 24.000 bytes de contexto, con margen para metadatos. El prompt completo tiene un máximo explícito de 32 KiB; una entrada que no quepa se rechaza antes de llamar al proveedor. Los fragmentos de más de 65.536 caracteres se omiten completos. El backend indica si el contexto fue truncado. Esta política es conservadora y puede perder detalles útiles; no garantiza reconocer todos los secretos arbitrarios o etiquetas empresariales desconocidas. El estudiante debe usar muestras sintéticas para la demo y revisar los datos reales antes de habilitar un proveedor.

La respuesta JSON es cerrada: resumen, explicaciones por rule_id, impacto técnico, motivo de prioridad, revisión manual, limitaciones y respuesta opcional a la pregunta. No admite campos severity, RuleStatus, evidence ni Findings nuevos. Se exige exactamente una referencia por cada Finding enviado: IDs ajenos, faltantes o duplicados se rechazan. También se rechazan instrucciones explícitas de configuración en las explicaciones. Estas restricciones protegen el contrato; la prosa generada sigue requiriendo revisión humana.

## API y fallos

| Ruta/caso | Comportamiento |
|---|---|
| `GET /api/v1/ai/health` | Solo enabled, gateway_reachable y model_configured. No infiere disponibilidad del modelo a partir de salud HTTP |
| `POST /api/v1/analyses/{id}/ai-explanation` | Consulta únicamente contexto del backend; request opcional `{question: ...}` |
| ID inexistente o contexto expulsado | 404; sin llamada al modelo |
| Sin Findings | Explicación determinista; sin llamada al modelo, incluso con IA desactivada |
| IA desactivada | AI_DISABLED |
| Conexión imposible | AI_GATEWAY_UNAVAILABLE |
| 401/403 | AI_AUTH_ERROR, sin retry |
| 400/404 o modelo ausente | AI_MODEL_UNAVAILABLE, sin retry |
| 429 | AI_RATE_LIMITED, como máximo un retry |
| 5xx | AI_UPSTREAM_ERROR, como máximo un retry |
| Timeout | AI_TIMEOUT, como máximo un retry |
| JSON/contrato inválido | Una sola reparación; si sigue inválido, AI_INVALID_RESPONSE |
| ID inventado/duplicado o falta de cobertura | AI_INVALID_RESPONSE; no se aceptan nuevas referencias |

El cliente usa solo `POST /v1/chat/completions`, modelo concreto, sin streaming de tokens, tools, MCP, A2A, Responses API ni auto-routing. El transporte lee con límite la respuesta HTTP (128 KiB). No registra cuerpos, prompts ni claves. Los reintentos están acotados a 0 o 1. Una reparación vuelve a usar el contexto seguro, sin reenviar la respuesta inválida. En el peor caso hay cuatro intentos HTTP, con timeout de 15 s por intento por defecto. La UI mantiene visibles los Findings ante cualquier fallo de IA.

## Configuración e inicio

Las variables están descritas en `.env.example`, sin secretos. No se carga automáticamente un `.env`: definir variables en la terminal que inicia FastAPI. La IA está desactivada por defecto; base URL `http://127.0.0.1:20128/v1`, timeout 15 s y máximo un retry. El modelo queda vacío por defecto; el ID verificado para esta rama es `gemini/gemini-3.5-flash-lite`. `httpx>=0.28,<0.29` pasa a runtime. Streamlit está en el extra `ui`; se instaló en el entorno virtual existente (versión observada 1.66.1). El proyecto configura Streamlit solo en loopback, carga máxima de 2 MiB y sin telemetría de uso.

Desde `C:\Users\Gamer\Desktop\grupo-1\Proyecto-Titulo-Cisco-IOS`, terminal API:

```powershell
$env:PYTHONUTF8 = '1'
$env:NETAUDIT_AI_ENABLED = 'false'
.\.venv\Scripts\python.exe -m uvicorn ios_auditor.api.app:app --host 127.0.0.1 --port 8000
```

Terminal UI, mismo directorio:

```powershell
.\.venv\Scripts\python.exe -m streamlit run apps/streamlit/app.py --server.address 127.0.0.1 --server.port 8501
```

Abrir `http://127.0.0.1:8501`. Para usar la configuración validada, definir en el proceso de FastAPI:

```powershell
$env:NETAUDIT_AI_ENABLED = 'true'
$env:NETAUDIT_AI_BASE_URL = 'http://127.0.0.1:20128/v1'
$env:NETAUDIT_AI_MODEL = 'gemini/gemini-3.5-flash-lite'
$env:NETAUDIT_AI_TIMEOUT_SECONDS = '30'
$env:NETAUDIT_AI_MAX_RETRIES = '0'
# NETAUDIT_AI_API_KEY debe provenir del almacén local; no incluir su valor en scripts o Git.
```

La clave se mantiene fuera del repositorio. `.env` sigue ignorado y `.env.example` contiene
solo valores de ejemplo sin credenciales. La configuración local validada de OmniRoute limita
la clave NetAudit a Google AI Studio y al modelo indicado, sin autorresolución y con presupuesto
de razonamiento de 128 tokens; ver [diagnóstico y ajuste](registro-validacion-final-ia.md#configuración-local-validada).
No es necesario resolver `/v1/models` para seleccionar este modelo: se verificó el catálogo
administrativo específico del proveedor. La aplicación no carga automáticamente archivos de entorno.

## Pruebas y evidencia

La suite normal usa fakes, MockTransport, TestClient y AppTest; no llama modelos ni dispositivos reales. Cubre secretos Cisco, claves privadas, inyección como dato, límites, settings, contratos, errores, retries, reparación, referencias, registro de contextos, preservación de resultados, health seguro, errores de UI, chat por ID y limpieza de campos SSH. Se añadieron 97 casos a las 703 pruebas integradas. Resultado final: **800 passed, 1 warning in 19.87s**, con 0 failed y 0 skipped; el warning conocido es de Starlette/AnyIO. `pip check` no encontró dependencias incompatibles.

Prueba live opcional fuera de `testpaths`, sin ejecución automática ni en CI:

```powershell
# Solo después de validar gateway/modelo y activarlos por entorno.
$env:NETAUDIT_RUN_LIVE_AI_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest tests_live/test_ai_live.py -q
```

Durante el corte inicial de implementación no se ejecutó ese test live opcional: aún no había modelo confirmado. La validación posterior sí realizó llamadas reales mediante FastAPI y Streamlit AppTest, registradas en el documento de cierre; no se atribuye esa ejecución al archivo optativo de pytest. No hubo SSH real. Una prueba HTTP real del backend cargó la muestra sintética insegura: 14 evaluaciones, 12 Findings, creación HTTP 201 y error AI_DISABLED 503; la posterior consulta del análisis fue idéntica. FastAPI y Streamlit respondieron a sus checks de salud y se inspeccionó la pantalla inicial de la UI. Los procesos temporales de verificación se detienen al cerrar la revisión.

El [guion](guion-demo-fase-2.md) y la [lista de capturas manuales](evidencias-ai/README.md) separan la demo determinista reproducible, la inferencia real ya validada y las capturas externas del MVP anterior al refinamiento visual.

## Límites y próximos pasos

El bloqueo histórico de `/v1/models` dejó de impedir la validación: el catálogo del proveedor
y la inferencia real confirmaron Gemini 3.5 Flash-Lite. Las tres pruebas secuenciales fueron
correctas y las dos respuestas integrales pasaron Pydantic. La prosa sigue requiriendo revisión
humana; el sanitizador puede acortar frases que contienen referencias a credenciales.
No hay autenticación ni autorización multiusuario: la configuración versionada de API/UI
mantiene loopback. La prueba desde un segundo PC por Radmin fue reportada por el estudiante;
no implica un despliegue productivo ni cambia esa configuración. Los contextos solo viven en
memoria; el MVP se ejecuta con un worker. El refinamiento UI/UX corresponde a un incremento posterior.

Persistencia PostgreSQL, interfaz multiusuario, reportes finales e integración de otros proveedores quedan fuera de este cambio. No se hizo push, PR ni merge a main. La carpeta local `Entregables-APT/Fase-2/Evaluacion-2/` se preserva y se excluye del stage.

Referencias de implementación: [timeouts de HTTPX](https://www.python-httpx.org/advanced/timeouts/), [MockTransport de HTTPX](https://www.python-httpx.org/advanced/transports/), [AppTest de Streamlit](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
