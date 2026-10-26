# Cierre del incremento de integración IA: baseline funcional

**Cierre documental:** 26 de octubre de 2026. **Rama:** `feature/ai-explainer-ui`.
**Baseline de código:** `3b7f916413927be8c5fa4fff3d2c6f54464e12a4`.
Este registro documenta validaciones realizadas el 25 de octubre; no ejecuta un nuevo
incremento de UI/UX ni cambia el estado de main.

## Historia y alcance del corte

- `7c7d13b89cd1c7d9a7bbc4d652cc159998247df9`: integración de Evaluación 2 en esta rama,
  conservando las 21 reglas y ocho evidencias/comandos de la arquitectura integral.
- `3b7f916413927be8c5fa4fff3d2c6f54464e12a4`: capa explicativa sanitizada, FastAPI,
  contrato Pydantic, repositorio temporal y Streamlit básico.
- El commit documental que incorpora este registro identifica el cierre; no se crea
  una nueva versión de la lógica, un tag, push, PR ni merge a main.

El refinamiento visual posterior parte de este **MVP funcional anterior al refinamiento
UI/UX**. Se conservan sus componentes y diseño existentes. Persistencia relacional,
reportes finales y autenticación multiusuario permanecen fuera de este cierre.

## Arquitectura validada y autoridad de los resultados

```text
Cisco IOS/IOS XE -> Netmiko de solo lectura
                 (o evidencias sintéticas en la validación offline)
 -> CiscoConfParse / TextFSM
 -> motor determinista -> evaluaciones y Findings
 -> snapshot sanitizado del backend -> FastAPI
 -> OmniRoute -> Google AI Studio -> Gemini 3.5 Flash-Lite
 -> JSON validado por Pydantic en FastAPI -> Streamlit
```

Streamlit solicita el análisis o una explicación al backend; no llama directamente al
proveedor. El motor determina PASS, FAIL, NOT_APPLICABLE, NOT_EVALUATED y ERROR, la
severidad y la evidencia. Solo FAIL produce Findings. La IA se ejecuta después y solo
añade explicación, impacto, prioridad justificada y orientación de revisión manual.
No puede crear Findings, cambiar rule_id, estados, severity o evidence ni sustituir reglas.

`src/ios_auditor/ai/` no importa Netmiko ni collectors. El cliente solo envía mensajes
a chat/completions, sin tools, acceso SSH, comandos Cisco ejecutables ni funciones de
administración. La UI solo utiliza BackendClient/FastAPI. No se abrió una nueva sesión
SSH desde IA ni se modificaron dispositivos.

## Inferencia real y repetibilidad

Proveedor oficial: **Gemini (Google AI Studio)**, identificador `gemini`.
Modelo: **`gemini-3.5-flash-lite`**.
ID exacto de OmniRoute: **`gemini/gemini-3.5-flash-lite`**.

| Comprobación del 25 de octubre | Resultado observado |
|---|---|
| Google directo, solicitud mínima | Headers recibidos, HTTP 200, NETAUDIT_AI_OK, 1,701 s |
| OmniRoute, configuración final | HTTP 200, NETAUDIT_AI_OK, 1,731 s |
| Repetición secuencial 1 | HTTP 200, 1,877 s |
| Repetición secuencial 2 | HTTP 200, 1,560 s |
| Repetición secuencial 3 | HTTP 200, 1,557 s |
| Criterio GO | 3/3, todas inferiores a 30 s, mismo proveedor |
| Explicación integral | HTTP 200, source ai, 17 Findings, 7,242 s |
| Pregunta conversacional | HTTP 200, source ai, 8,318 s |
| Contrato | Dos JSON completos validados con Pydantic, 17 IDs, sin reparación final |
| Invariantes | Resultado integral, contexto backend y análisis UI idénticos antes/después |

La pregunta fue «¿Cuál es el hallazgo que debería revisar primero y por qué?». Gemini
priorizó IOS-ADM-001, Telnet en líneas VTY, por exposición de credenciales y comandos
en texto plano. No afirmó haber aplicado cambios al router. Las trazas identificaron
la conexión Google AI Studio, el modelo elegido y origen upstream, sin caché de respuesta.
Los resultados seleccionados están en [validacion-gemini.json](evidencias-ai/validacion-gemini.json).

El escenario integral usó fixtures sintéticas existentes y el servicio
`scripts/evaluacion_2/offline_integral.py`: 21 evaluaciones, ocho evidencias, 17 FAIL,
3 PASS, 1 NOT_EVALUATED y 17 Findings determinados antes de IA. La inferencia fue real;
las fuentes Cisco fueron sintéticas. No se atribuyen estas cifras a una nueva captura de
un router real. El modo archivo, por separado, ejecuta 14 reglas y produce 12 Findings
para la muestra insegura. Las siete reglas operacionales requieren evidencia adicional.

FastAPI y Streamlit se iniciaron realmente en loopback. Streamlit AppTest ejecutó el
botón y la pregunta usando el DTO integral real y llamadas HTTP reales al backend;
no se sustituyeron las respuestas de Gemini. La suite ordinaria de pytest sí usa mocks
y permanece independiente de redes externas y modelos reales.

## Configuración local validada

OmniRoute conservó la versión 3.8.50. Su catálogo administrativo específico permitió
identificar el modelo sin depender de /v1/models. El thinking predeterminado consumía
casi toda la salida del cliente: 3.836–3.840 tokens de razonamiento en respuestas de
3.996 tokens. El backend rechazó esos resultados incompletos con AI_INVALID_RESPONSE.
El intento reasoning_effort=none produjo 400; no se utilizó como solución.

La configuración funcional añade una regla de OmniRoute limitada a la clave local de
NetAudit: sourceEffort missing, effortMode force, targetEffort low, budgetAction set y
budgetTokens 128. targetKind keep conserva modelo y proveedor. La clave queda limitada
a la conexión Google AI Studio y al modelo elegido, con autorresolución desactivada y
caché en bypass. Esto es configuración externa; no modifica NetAudit ni otras conexiones.
En las ejecuciones finales la traza reportó cero tokens de razonamiento y JSON completos.

NetAudit se activó por variables de proceso: modelo exacto, URL de gateway local,
timeout 30 s y cero retries de transporte. Los defaults del código no se cambiaron:
IA desactivada, modelo vacío, timeout 15 s y hasta un retry. La aplicación no carga .env
automáticamente. La clave permanece solo en el almacén local y el entorno de ejecución;
no se publica su valor, identificador de credencial, vencimiento ni contenido del .env.

## Resiliencia y seguridad

Después de una explicación y conversación válidas se simuló una sola indisponibilidad
cambiando la URL de IA a un puerto loopback cerrado, solo en el proceso de validación.
La solicitud produjo HTTP 503 / AI_GATEWAY_UNAVAILABLE. Se mantuvieron 21 evaluaciones,
17 Findings visibles, el análisis completo y el aviso de Streamlit. La URL original se
restauró en finally y el health de OmniRoute respondió 200; no se detuvo ni alteró el gateway.
Esta prueba acredita degradación controlada por indisponibilidad, no una caída física del proceso.

La sanitización sigue activa antes de truncar: elimina secretos reconocibles, credenciales,
direcciones y hosts explícitos de los fragmentos enviados. El modelo recibió solo Findings
sintéticos sanitizados; no se expusieron secretos reales al modelo. Las claves de autenticación
se usan en transporte HTTP, fuera del prompt. El contrato no admite campos para modificar
severidad, evidencia o Findings y rechaza IDs ajenos, faltantes o duplicados. La revisión de
imports y las pruebas confirman la separación de IA, UI, reglas y collectors.

`.env` está ignorado y no versionado; `.env.example` conserva placeholders sin credenciales.
La revisión de patrones de claves, tokens y claves privadas en texto versionado y diff
solo detectó delimitadores PEM sintéticos en tests de sanitización. No se copian datos
de cuentas, hosts reales, configuraciones completas ni salidas SHOW originales al registro.
La sanitización es conservadora y puede acortar frases; Pydantic valida estructura, no
certifica toda la prosa técnica. La explicación sigue requiriendo revisión humana.

## Pruebas automatizadas de cierre

Precheck del 26 de octubre: **800 passed, 0 failed, 1 warning in 13.47s**.
Comprobación final del 26 de octubre: **800 passed, 0 failed, 1 warning in 12.44s**.
La suite normal no llama al proveedor ni abre SSH. La advertencia conocida corresponde
a la deprecación de anyio.abc.BlockingPortal en Starlette. Este cierre no repite las llamadas
de inferencia del 25 de octubre ni presenta sus métricas como una ejecución nueva.

## Evidencias manuales y baseline visual

El estudiante reportó una prueba correcta desde un segundo PC mediante Radmin, capturas
actuales de Streamlit guardadas externamente y una captura de PowerShell con 800 tests.
Las capturas corresponden a **«ANTES — MVP funcional previo al refinamiento visual»**.
Sus archivos, rutas y configuración de acceso no se inspeccionaron en este cierre;
la prueba Radmin se registra como validación manual reportada, separada de la automatizada.
No implica aprobación de exposición productiva ni cambia el enlace loopback versionado.

No se reemplazan ni recrean capturas. El [índice de evidencias](evidencias-ai/README.md)
conserva esa distinción para una comparación posterior. No se aplicó el prompt de diseño
ni se modificó UI/UX. La carpeta local Entregables-APT/Fase-2/Evaluacion-2/ sigue fuera del
stage y del commit. La rama feature/evaluacion-2-validacion conserva su estado independiente.
