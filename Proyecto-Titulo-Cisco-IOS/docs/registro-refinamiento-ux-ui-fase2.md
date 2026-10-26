# Incremento de Fase 2 — Refinamiento UX/UI de NetAudit

Fecha: 26 de octubre de 2026. Rama `feature/ui-ux-refinement`.
Baseline: `e0b7c0f`, integración previa de IA en main mediante PR #5.
Este incremento sigue siendo Fase 2. No modifica lógica de auditoría ni arquitectura.

## Alcance visual y navegación

Se conserva Streamlit 1.66.1, sin dependencias nuevas ni frontend separado. La cabecera
identifica NetAudit, Cisco IOS/IOS XE, solo lectura y el principio «Las reglas detectan.
La evidencia demuestra. La IA explica». La sidebar agrupa origen Archivo/Dispositivo,
conexión, estado del sistema y modelo validado. La contraseña sigue en un input password
y sus campos se limpian tanto ante éxito como ante fallo.

Las pestañas Resumen, Hallazgos, Asistente IA y Evidencia separan los resultados de la
explicación. Las tarjetas y métricas muestran los valores del DTO del backend: total de
evaluaciones, los cinco RuleStatus, número de Findings y distribución por severidad.
No se deduce ni cambia el estado técnico. Las evidencias y explicaciones por regla
permanecen colapsadas hasta que el usuario las abre.

Hallazgos permite filtrar por severidad, rule_id y texto de nombre, mensaje o recomendación.
El orden de presentación es CRITICAL, HIGH, MEDIUM, LOW, INFO; no modifica el orden ni
los valores del análisis original. No se inventa una categoría. Nuevo análisis limpia
resultado visual, filtros, explicación, conversación y metadatos de ese análisis; no elimina
archivos, dispositivos, contextos del backend ni preferencias ajenas.

## Estados observables, sin inferencias para los indicadores

El cliente UI utiliza únicamente FastAPI:

| Indicador | Fuente y significado |
|---|---|
| NetAudit | GET /health: backend responde status ok |
| Motor determinista | GET /api/v1/rules: catálogo del motor disponible; no ejecuta reglas para el indicador |
| OmniRoute | gateway_reachable de GET /api/v1/ai/health: accesibilidad HTTP reportada por backend |
| IA | enabled, model_configured y gateway_reachable; verde solo tras una respuesta source ai realmente obtenida en esa sesión |

Un health accesible no demuestra inferencia. Antes de una respuesta real, IA muestra
«Configurada · sin inferencia de prueba». Tras una respuesta validada muestra
«Disponible · respuesta verificada». Los fallos actualizan el estado sin borrar el análisis.
No se infiere disponibilidad del proveedor, cuota o modelo solo por HTTP. El endpoint
actual no informa el ID activo: Gemini 3.5 Flash-Lite se identifica como modelo validado
del baseline, sin presentarlo como descubrimiento dinámico de configuración.

Los chequeos se realizan al abrir la sesión, al pulsar Actualizar estado o en la próxima
interacción si pasaron 60 segundos. No hay polling automático, bucles ni llamadas Gemini
para comprobar salud. Las lecturas HTTP tienen timeouts acotados. Cuando IA está
deshabilitada, el gateway figura como no comprobado/deshabilitado, no como caído.

## Temas y accesibilidad

Se agregan theme.light y theme.dark y sus variantes de sidebar en .streamlit/config.toml,
con soporte nativo de Streamlit. La selección se realiza en el menú ⋮, Light/Dark/System.
No se utiliza JavaScript ni manipulación del DOM. El CSS se limita a clases propias de
cabecera, separación y puntos de estado, y a la clase st-key documentada para containers.
Los indicadores siempre combinan texto y color. Los KPIs usan contenedores flexibles con
wrap y tamaños nativos; la página no fuerza una cuadrícula rígida de seis columnas.
Los errores internos no muestran tracebacks crudos en la UI.

La documentación oficial describe los [temas nativos](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)
y las [clases de container basadas en key](https://docs.streamlit.io/develop/api-reference/layout/st.container).

## Exportaciones y protección de datos

JSON descarga una proyección explícita del DTO del backend. CSV descarga todos los
Findings, independientemente de los filtros visuales. No se incluyen credenciales SSH,
API keys, campos desconocidos, conexiones, raw_output ni configuraciones completas.
Los textos se redactan mediante la función pura de sanitización existente, reutilizada
sin modificar su código. Este uso no proporciona acceso al cliente IA ni al gateway.
Los CSV neutralizan fórmulas de hoja de cálculo con prefijo de comilla, conservando
Unicode y el escape CSV. Los tests incluyen secretos sintéticos y fórmulas maliciosas.

El resultado original permanece intacto: la UI y las descargas usan una copia de
presentación. Hashes mostrados corresponden a la evidencia original publicada por backend,
no se recalculan para el texto redactado. La redacción conservadora existente puede
acortar nombres o frases técnicas que contienen términos como enable password; no se
relajó ese redactor durante este incremento.

La conversación continúa usando el identificador del análisis del backend y su contrato
existente. El historial solo vive en la sesión. La pregunta se redacta antes de conservarse
o enviarse; no se agregan herramientas, prompts ni facultades a la IA.

## Validación y límites

Baseline pytest: **800 passed, 0 failed, 1 warning in 15.16s**.
Se conservaron todas las pruebas previas y se añadieron 15 casos para filtros e invariancia,
exportación segura, protección CSV, estados sin inferencia, caché de salud, Nuevo análisis
y resiliencia. La fixture de salud de los tests UI anteriores evita red real en pytest.
Las pruebas automatizadas normales no consumen modelos ni abren SSH.
Resultado final: **815 passed, 0 failed, 1 warning in 16.20s**. El warning ya existía
y corresponde a la deprecación BlockingPortal de AnyIO en Starlette.

En el navegador local real se validaron pantalla inicial, sidebar, análisis de archivo
sintético, KPIs, búsqueda IOS-AUTH-003, evidencia colapsable, explicación Gemini real,
conversación, descargas JSON/CSV, temas y estados de servicio. El archivo inseguro produce
14 evaluaciones y 12 Findings; no se presenta como una ejecución de 21 reglas.
Se revisaron visualmente 1920×1080, 2560×1440 y 1366×768, midiendo en el DOM la
ausencia de desbordamiento horizontal. Se restauró el viewport normal al terminar.
Nuevo análisis se comprobó también en navegador: desaparecieron referencia anterior,
pestañas y conversación, y se recuperó la pantalla inicial; luego se analizó de nuevo
el archivo sintético para dejar una vista de revisión.

Se detuvo una sola vez la instancia local verificada de OmniRoute y se mantuvieron los
Findings y el aviso global de IA no disponible. Mientras el gateway estaba apagado, otro
análisis de archivo respondió HTTP 201 y el escenario integral sintético conservó 21
evaluaciones, ocho evidencias y 17 Findings. Se restauró la misma instalación y su health
volvió a 200; no se cambiaron versión, proveedores, claves, políticas ni configuración.
Una nueva explicación real volvió a mostrar respuesta verificada. Se comparó el DTO
original completo antes y después de explicación, chat, caída y restauración: idéntico.

El modo Dispositivo conserva el formulario y recorrido probado con fakes del backend;
no se realizó una nueva sesión SSH real sin las credenciales del estudiante. La API
actual agrupa autenticación y conexión SSH en DEVICE_ANALYSIS_FAILED: la UI no inventa
una causa más específica ni modifica el contrato. Hostname, IP, plataforma detectada y
versión se muestran únicamente si el backend los publica; el DTO vigente no los expone
y la UI no los reconstruye desde credenciales transitorias.

La configuración server y browser de Streamlit se conserva. Las dos instancias UI
existentes necesitaron reiniciarse para cargar los módulos nuevos: loopback y la destinada
al acceso previamente usado con Radmin. Esta última conservó exactamente su enlace
0.0.0.0 y puerto 8501; se utilizó el venv ya validado del proyecto. No se cambiaron
firewall, VPN, IP ni configuración de red. Antes del reinicio, esa instancia retenía un
módulo anterior y no cargaba los indicadores nuevos. Tras el reinicio se comprobó desde
el mismo equipo su interfaz mediante el alias local 127.0.0.2:8501: estados correctos,
sin error UI y análisis de archivo con 14 evaluaciones y 12 Findings. Esto verifica la
instancia que conserva el enlace existente; la prueba desde otro PC del baseline sigue
siendo evidencia manual previa y no se declara repetida desde un segundo equipo.

## Evidencia ANTES / DESPUÉS

Las capturas externas guardadas por el estudiante siguen representando
**ANTES — MVP funcional previo al refinamiento visual** y no se tocaron. La captura
PowerShell de 800 tests se mantiene. Las capturas del navegador de esta revisión son
reales, independientes y corresponden a **DESPUÉS — interfaz UX/UI refinada**.

Para la comparación académica de Fase 2 se recomiendan capturas reales de dashboard
light/dark, KPIs, filtros, evidencia, explicación, chat, servicios online, caída y
exportaciones: 01-dashboard-light, 02-dashboard-dark, 03-resultados-kpi,
04-hallazgos-filtros, 05-evidencia-tecnica, 06-asistente-ia, 07-chat-ia,
08-servicios-online, 09-ia-no-disponible y 10-exportaciones.

Este incremento queda sin commit, push, PR ni merge para revisión visual. La carpeta
Entregables-APT/Fase-2/Evaluacion-2/ permanece excluida e intacta. El reporte de entrega
registra el pytest final, dimensiones de validación y diff definitivo.
