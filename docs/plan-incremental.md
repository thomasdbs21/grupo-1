# Plan incremental de desarrollo

## 1. Propósito

El proyecto se construirá mediante incrementos pequeños, verificables y respaldados por Git. Cada incremento deberá producir una versión funcional o una mejora comprobable, con alcance delimitado y evidencia de validación.

## 2. Principios del desarrollo incremental

- Una tarea por alcance controlado.
- Pruebas pertinentes antes de cerrar un incremento.
- Commits pequeños, coherentes y descriptivos.
- No implementar funciones futuras anticipadamente.
- Revisar seguridad y ausencia de secretos en cada etapa.
- Registrar decisiones en los documentos núcleo (CORE) y en la documentación técnica oficial.
- Validar progresivamente los escenarios en laboratorios virtuales autorizados; GNS3 permanece como opción futura.
- Incorporar inteligencia artificial solo después de disponer de un motor técnico determinista y validado.

## 3. Incremento 0 — Preparación del repositorio

**Estado:** COMPLETADO.

Incluye:

- Repositorio Git.
- Rama `main`.
- Repositorio privado en GitHub.
- Entorno virtual `.venv`.
- Archivo `.gitignore`.
- Archivo `AGENTS.md`.
- Carpeta `docs`.
- Documentación técnica inicial.

Criterios de cierre:

- Repositorio limpio.
- Primer commit realizado.
- Push realizado a GitHub.
- `.venv` fuera del seguimiento de Git.

## 4. Incremento 1 — Analizador offline de running-config

**Estado:** COMPLETADO.

**Objetivo:** analizar un archivo local `running-config` y producir evaluaciones y `findings` trazables.

Incluye:

- Proyecto Python definido mediante `pyproject.toml`.
- Estructura basada en `src/`.
- `ciscoconfparse2`, usando la clase `CiscoConfParse`.
- Modelos tipados.
- Lectura y hash del archivo.
- Contexto normalizado e inmutable.
- Tres reglas piloto.
- Salida JSON.
- Pruebas con pytest.
- Configuraciones de ejemplo correctas e incorrectas, sin secretos.
- CLI básica.
- README con instalación y uso.

Fuera de alcance:

- SSH y Netmiko.
- FastAPI.
- PostgreSQL, SQLAlchemy y Alembic.
- Streamlit.
- Inteligencia artificial.
- TextFSM y comandos `show`.

Criterios de aceptación:

- Un archivo correcto produce los resultados esperados.
- Un archivo incorrecto preparado para el escenario produce los tres `findings` previstos.
- Una evaluación `PASS` no genera un `Finding`.
- Una evaluación `FAIL` sí genera un `Finding`.
- Los errores de entrada, parsing y reglas se reportan correctamente sin convertirse en resultados falsos.
- Todas las pruebas del incremento están aprobadas.

## 5. Incremento 2 — Registro y metadatos de reglas

**Estado:** COMPLETADO.

Incluye:

- Tres archivos de metadatos YAML, uno por regla piloto.
- Carga segura, controlada y validada mediante `yaml.safe_load`.
- Modelo `RuleMetadata` inmutable.
- Registro central de reglas con consulta por ID y orden determinista.
- Versionado de definiciones.
- Activación o desactivación mediante `enabled`.
- Ejecución exclusiva de reglas habilitadas.
- Validación de consistencia entre IDs YAML y clases Python.
- Lógica de evaluación mantenida exclusivamente en Python.

Criterios de cierre cumplidos:

- Los tres YAML oficiales cargan correctamente.
- Los campos obligatorios, versiones, severidades e IDs se validan.
- Los duplicados y YAML inválidos se rechazan con errores comprensibles.
- Una regla deshabilitada no produce evaluación ni hallazgo.
- Las 19 pruebas anteriores conservan su comportamiento.
- Las 33 pruebas totales están aprobadas.

## 6. Incremento 3 — API FastAPI

**Estado:** COMPLETADO.

Incluye:

- Estado de salud y consulta de reglas habilitadas.
- Carga multipart de archivos `.cfg`, `.conf` y `.txt`.
- Análisis síncrono en memoria con límite de 2 MiB.
- Consulta por UUID del resultado, evaluaciones y `findings`.
- Repositorio temporal concurrente de hasta 100 análisis.
- Modelos de respuesta tipados con Pydantic.
- Manejo estructurado de errores y logging seguro.
- Documentación OpenAPI en `/docs` y `/redoc` para desarrollo local.
- Compatibilidad completa con la CLI existente.

Criterios de cierre cumplidos:

- La API no escribe archivos subidos ni confía en rutas del cliente.
- Las respuestas no contienen rutas absolutas ni configuraciones completas.
- La configuración incorrecta produce tres hallazgos y la correcta ninguno.
- La expulsión del análisis más antiguo al superar 100 está probada.
- Las 33 pruebas anteriores continúan aprobadas.
- Las 59 pruebas totales están aprobadas.

## 7. Incremento 4 — SSH de solo lectura

**Estado:** COMPLETADO.

Incluye:

- Netmiko como recolector SSH de solo lectura para Cisco IOS e IOS XE.
- Lista blanca inmutable con cuatro comandos autorizados.
- Validación exacta de comandos antes de conectar.
- Recolección de uno o varios comandos en una única sesión.
- Evidencia inmutable con UUID, fecha UTC, contenido original y normalizado, y SHA-256.
- Protección de credenciales y salidas en representaciones y errores.
- Manejo seguro de autenticación, timeout, conexión y cierre.
- Protocolo `RunningConfigCollector` para desacoplar infraestructura y aplicación.
- Orquestador `analyze_collected_running_config()`.
- Integración de `show running-config` con `analyze_bytes()` y las tres reglas piloto.
- Identidad de hash entre `CommandEvidence` y `AnalysisResult`.
- Validación manual controlada con un CSR1000v IOS XE 16.9.5 ejecutado en VirtualBox.

No incluye comandos de configuración ni cambios sobre dispositivos.

Criterios de cierre cumplidos:

- El recolector rechaza comandos no autorizados antes de abrir una conexión.
- No utiliza `send_config_set()`, `config_mode()` ni comandos de configuración.
- Las reglas reciben únicamente `AnalysisContext` y no conocen Netmiko ni credenciales.
- Las 19 pruebas unitarias del recolector se ejecutan sin conexión real.
- Las 18 pruebas nuevas del orquestador se ejecutan con recolectores falsos, mocks y spies.
- La suite alcanzó 78 pruebas aprobadas después del recolector y 96 después de la integración.
- La validación real inicial recopiló cuatro comandos autorizados en una sesión y cerró la conexión.
- La validación integrada del 14 de julio de 2026 obtuvo tres evaluaciones, cero findings y `VALIDACION_INTEGRADA_OK`.

Limitaciones al cierre del Incremento 4:

- Solo `show running-config` está integrado con el analizador determinista.
- Al cierre del Incremento 4, los otros comandos `show` todavía no se estructuraban mediante TextFSM; esta limitación fue abordada en el Incremento 5.
- FastAPI no exponía conexiones SSH; esta limitación fue abordada en el Incremento 7.
- No existe persistencia PostgreSQL para ejecuciones o evidencias.
- No existe integración SSH con inteligencia artificial.
- `evidence_id` y `analysis_id` persistentes quedan para incrementos posteriores.

## 8. Incremento 5 — Comandos show y TextFSM

**Estado:** COMPLETADO.

Incluye:

- TextFSM declarado directamente como `textfsm>=2.1,<3`.
- Plantillas propias para `show version`, `show ip interface brief` y `show ip ssh`.
- Parsing separado de Netmiko y sin acceso a red.
- Modelos tipados y `OperationalContext` inmutable sin salidas completas.
- Servicio `parse_collected_show_evidence()` para validar SHA-256, normalización, comando y fecha UTC.
- Regla operacional `IOS-IF-001` separada del `RuleRegistry` de `running-config`.
- Rechazo de filas de interfaz desconocidas y normalización de espacios en `administratively down`.
- Pruebas automatizadas sin conexiones reales.

Criterios de cierre cumplidos:

- Las tres salidas autorizadas producen modelos estructurados.
- `show running-config` continúa usando `ciscoconfparse2` y `CiscoConfParse`.
- `OperationalContext` y la colección de interfaces son inmutables.
- `IOS-IF-001` produce `FAIL` únicamente ante una interfaz `up` con protocolo distinto de `up` e ignora `administratively down`.
- Se agregaron 28 pruebas: 12 del parser, 9 del servicio y 7 de la regla.
- La suite pasó de 96 a 122 pruebas y luego a 124 con dos regresiones; las 124 quedaron aprobadas después del merge.
- La validación real con CSR1000v IOS XE 16.9.5 en VirtualBox produjo tres evidencias, un `execution_id`, hashes correctos, tres modelos, una interfaz evaluable, cero inconsistencias, `IOS-IF-001` en `PASS`, sesión cerrada y `VALIDACION_TEXTFSM_OK`.
- La implementación se registró en `0ca7cf3`, Pull Request #4, y se integró mediante el merge `b7be551`.

Limitaciones al cierre del Incremento 5:

- Solo tres comandos `show` tienen parsing estructurado.
- Existe una sola regla operacional.
- El servicio procesa una evidencia por llamada.
- FastAPI no procesaba resultados operacionales; esta limitación fue abordada por los Incrementos 6 y 7.
- No existe persistencia ni integración operacional con inteligencia artificial.
- Las plantillas se validaron únicamente con las variantes disponibles.

## 9. Incremento 6 — Orquestación multifuente y análisis integral del dispositivo

**Estado:** COMPLETADO.

**Objetivo:** construir un servicio que produzca una auditoría integral, inmutable y trazable de un dispositivo a partir de una única sesión SSH de solo lectura.

Flujo implementado:

1. Abrir una única sesión mediante `NetmikoCollector`.
2. Recopilar exclusivamente `show running-config`, `show version`, `show ip interface brief` y `show ip ssh`.
3. Producir una `CommandEvidence` por comando.
4. Exigir un mismo `execution_id` para las cuatro evidencias.
5. Validar comando, fecha UTC, UUID, normalización y SHA-256.
6. Analizar `show running-config` con el flujo existente basado en CiscoConfParse.
7. Analizar los tres comandos `show` con el flujo existente basado en TextFSM.
8. Ejecutar las tres reglas actuales de `running-config`.
9. Ejecutar `IOS-IF-001` sobre el contexto correspondiente.
10. Producir un resultado agregado, inmutable y trazable del dispositivo.
11. Conservar todas las evaluaciones.
12. Derivar `findings` únicamente de resultados `FAIL`.

Alcance incluido:

- Contrato de resultado integral.
- Validación estricta del conjunto de evidencias.
- Detección de comandos ausentes, duplicados o adicionales.
- Reutilización de servicios existentes.
- Orquestación de análisis de configuración y operacional.
- Resultado agregado inmutable.
- Evaluaciones completas.
- `Findings` derivados exclusivamente de `FAIL`.
- Errores sanitizados.
- Pruebas automatizadas sin SSH real.
- Validación manual controlada contra CSR1000v.
- Documentación e Informe Técnico N.º 4 al cierre.

Fuera del alcance:

- PostgreSQL.
- SQLAlchemy y Alembic.
- Streamlit.
- Pasarela de inteligencia artificial.
- Nuevos endpoints SSH de FastAPI.
- Nuevos comandos `show`.
- Nuevas reglas técnicas.
- Unificación general de todos los registros de reglas.
- Gestión definitiva de credenciales.
- Cambios automáticos en dispositivos.
- Incorporación de GNS3 o nuevas imágenes Cisco.

Criterios de cierre verificados:

- Los cuatro comandos son recopilados en una sola sesión.
- Existe exactamente una evidencia por comando y todas comparten el mismo `execution_id`.
- Los hashes son válidos.
- El resultado integral es inmutable.
- Se ejecutan tres reglas de configuración e `IOS-IF-001`.
- Todos los `FAIL` producen `findings`; `PASS`, `NOT_APPLICABLE`, `NOT_EVALUATED` y `ERROR` no los producen.
- Las fuentes ausentes, duplicadas o adicionales fallan explícitamente.
- Los errores no filtran información sensible.
- Todas las pruebas anteriores continúan aprobándose.
- La validación manual terminó con `VALIDACION_CSR1000V: OK`.
- La sesión SSH queda correctamente cerrada.

Resultado del incremento:

- Se implementaron `FullDeviceAnalysisResult`, `ValidatedEvidenceBatch`, `analyze_validated_evidence_batch()` y `collect_and_analyze_device()`.
- El flujo conserva por identidad las evidencias y el lote validado, y devuelve directamente el resultado integral.
- El SHA-256 se calcula sobre `raw_output.encode("utf-8")`; `normalized_output` se valida por separado y no es la entrada del hash.
- Se ejecutan `IOS-ADM-001`, `IOS-SRV-001`, `IOS-AUTH-001` e `IOS-IF-001`.
- Se agregaron 73 casos pytest: 14 del resultado integral, 27 del lote, 20 del orquestador puro y 12 de la integración SSH.
- La suite pasó de 124 a 197 pruebas y las 197 quedaron aprobadas.
- La validación manual se realizó una sola vez el 22-07-2026 contra una CSR1000v IOS XE 16.9.5 en VirtualBox.
- El resultado sanitizado confirmó una conexión, una desconexión, cuatro comandos y evidencias, un UUID común, fechas UTC, normalización e integridad válidas, tres contextos operacionales, cuatro evaluaciones y cero findings.
- Los cero findings demuestran que no hubo evaluaciones `FAIL`; no se conservó evidencia suficiente para afirmar que las cuatro evaluaciones fueran `PASS`.
- La implementación se registró en `f7e4398`, `ae832dd`, `92d82fd` y `5753768`.

Justificación del orden:

Este incremento se realizó antes de PostgreSQL para estabilizar primero el contrato que representa una auditoría completa. La persistencia posterior podrá diseñarse sobre dispositivos, ejecuciones, evidencias, evaluaciones y `findings` ya definidos.

## 10. Incremento 7 — API segura de análisis integral

**Estado:** COMPLETADO Y FUSIONADO.

Incluye:

- Endpoint `POST /api/v1/device-analyses` para invocar el flujo integral existente.
- Solicitud tipada con credenciales transitorias y validación estricta.
- Transformación explícita a una respuesta tipada y sanitizada.
- Exclusión de credenciales, host, configuraciones completas, salidas originales y contextos operacionales completos.
- Mapeo controlado de errores públicos.
- Compatibilidad con una sesión SSH de solo lectura, cuatro comandos autorizados, cuatro evidencias y tres contextos operacionales.
- Conservación de las cuatro evaluaciones deterministas existentes y derivación de `findings` únicamente desde `FAIL`.
- 265 pruebas aprobadas al cierre.

El incremento se cerró y fusionó mediante la Pull Request #8 y el merge commit `f405f57f46f2fc9e04b78ce529bfe974fa530f3d`.

## 11. Incremento 8 — Ampliación controlada del catálogo determinista de running-config

**Estado:** APROBADO Y PLANIFICADO; NO IMPLEMENTADO.

**Objetivo:** aumentar de cuatro a ocho las reglas del análisis integral mediante cuatro reglas nuevas de `running-config`, reutilizando `AnalysisContext`, `RuleRegistry` y los flujos actuales sin incorporar nuevas fuentes ni dependencias.

Reglas aprobadas:

| ID | Nombre | Severidad | Fuente |
|---|---|---|---|
| `IOS-ADM-002` | SSH versión 1 habilitada | `HIGH` | `running-config` |
| `IOS-SRV-002` | Servicios TCP/UDP pequeños habilitados | `MEDIUM` | `running-config` |
| `IOS-NTP-001` | Servidor NTP no configurado | `MEDIUM` | `running-config` |
| `IOS-LOG-001` | Servidor Syslog no configurado | `MEDIUM` | `running-config` |

Alcance incluido:

- Cuatro clases Python futuras y cuatro archivos YAML futuros.
- Ampliación del `RuleRegistry` de `running-config`.
- Evidencia mínima y sanitizada.
- Pruebas unitarias y de integración.
- Compatibilidad con la CLI, la API de archivos y la API integral sin cambios en el endpoint.
- Validación real posterior de solo lectura.

Decisiones obligatorias:

- Las reglas recibirán únicamente `AnalysisContext` inmutable y nunca credenciales.
- Ninguna regla accederá a SSH, Netmiko, base de datos, FastAPI o inteligencia artificial.
- Todas las evaluaciones se conservarán; solamente `FAIL` generará `findings`.
- Las excepciones inesperadas se representarán mediante `ERROR`.
- La lógica permanecerá en Python y los metadatos declarativos en YAML.
- La evidencia será la mínima necesaria y no expondrá direcciones, hostnames, claves ni parámetros sensibles.

Fuera del alcance:

- Nuevos comandos `show`, cambios en Netmiko o SSH y nuevas plantillas TextFSM.
- PostgreSQL, SQLAlchemy, Alembic, Streamlit, reportes e inteligencia artificial.
- GNS3, nuevas imágenes Cisco y cambios en dispositivos.
- Reglas OSPF, SNMP, consola o nomenclatura.

Criterios previstos de cierre:

- Las cuatro reglas nuevas respetan exactamente los contratos oficiales del catálogo.
- El análisis integral ejecuta ocho reglas sin cambiar el endpoint.
- Los resultados conservan todas las evaluaciones y solo los `FAIL` producen `findings`.
- Las evidencias de las reglas nuevas son mínimas y sanitizadas.
- Las excepciones inesperadas producen `ERROR`, no resultados técnicos falsos.
- Las pruebas anteriores y las nuevas quedan aprobadas sin conexiones reales.
- La validación manual posterior utiliza exclusivamente el flujo de solo lectura.

PostgreSQL permanece como incremento posterior; primero se ampliará y estabilizará el catálogo determinista sobre el contrato integral ya cerrado.

## 12. Persistencia futura — etapa por decidir

Incluye:

- PostgreSQL.
- SQLAlchemy.
- Alembic.
- Entidades `AnalysisRun`, `Device`, `Evidence`, `RuleEvaluation` y `Finding`.
- Historial de análisis.
- Almacenamiento de todas las evaluaciones y únicamente hallazgos derivados de `FAIL`.

## 13. Interfaz Streamlit futura — etapa por decidir

Incluye:

- Carga de configuraciones.
- Selección de dispositivos.
- Visualización de severidades.
- Presentación de evidencias sanitizadas.
- Recomendaciones técnicas validadas.
- Historial de análisis.

## 14. Reportes futuros — etapa por decidir

Incluye:

- JSON.
- HTML.
- PDF.
- Sanitización de información sensible.
- Resumen por severidad.
- Trazabilidad entre ejecución, evidencia, evaluación y hallazgo.

## 15. Inteligencia artificial opcional — etapa por decidir

Incluye:

- Pasarela independiente del motor de reglas.
- Sanitización previa de datos.
- Entrada estructurada basada en hallazgos validados.
- Explicaciones técnicas.
- Resúmenes.
- Priorización basada exclusivamente en severidades y criterios ya definidos.
- Respuesta técnica alternativa cuando la IA no esté disponible.
- Pruebas destinadas a detectar alucinaciones o alteraciones de resultados.

La IA no creará reglas, hallazgos ni evidencias y no cambiará estados o severidades.

## 16. Catálogo MVP y validación ampliada — etapa por decidir

Incluye:

- Implementación progresiva de 20 a 25 reglas.
- Escenarios correctos e incorrectos en laboratorios virtuales autorizados. GNS3 podrá evaluarse si se dispone legalmente de imágenes compatibles.
- Medición de verdaderos positivos.
- Revisión de falsos positivos.
- Revisión de falsos negativos.
- Cálculo de `precision`.
- Cálculo de `recall`.
- Medición del tiempo de análisis.
- Evidencias reproducibles para el informe del proyecto.

## 17. Estrategia de Git

- Mantener una rama `main` estable.
- Crear commits por incremento o cambio coherente.
- Utilizar mensajes convencionales cuando corresponda:
  - `feat:` para funcionalidades.
  - `fix:` para correcciones.
  - `test:` para pruebas.
  - `docs:` para documentación.
  - `chore:` para mantenimiento.
  - `refactor:` para cambios internos sin alterar comportamiento.
- Revisar `git diff` antes de cada commit.
- Ejecutar las pruebas pertinentes antes del commit.
- Realizar push solo después de validar el cambio.

No se define todavía un flujo complejo con múltiples ramas.

## 18. Definición de terminado

Una tarea se considera terminada cuando:

- Cumple el alcance acordado.
- No introduce funciones no solicitadas.
- Tiene pruebas cuando corresponde.
- Las pruebas pasan.
- No contiene secretos.
- Está documentada.
- El diff fue revisado.
- Tiene un commit coherente.
- Fue respaldada en GitHub.
- Las decisiones relevantes fueron registradas.

Cuando una tarea solicite explícitamente no realizar commit o push, dichos pasos quedarán pendientes y deberán informarse; la tarea documental podrá considerarse completada en su alcance local, pero no respaldada todavía.

## 19. Riesgos del desarrollo

| Riesgo | Mitigación breve |
|---|---|
| Expansión excesiva del alcance | Delimitar cada incremento y rechazar implementación anticipada. |
| Dependencia de imágenes Cisco | Verificar disponibilidad y licenciamiento antes de planificar escenarios. |
| Falsos positivos | Definir evidencia clara, excepciones y casos de prueba reproducibles. |
| Parsing incompleto | Conservar siempre la fuente original y registrar errores explícitos. |
| Diferencias entre versiones IOS | Registrar plataforma y versión; probar variantes soportadas. |
| Credenciales expuestas | Usar variables de entorno o gestores de secretos y sanitizar salidas. |
| IA que inventa explicaciones | Limitarla a datos validados y probar que no altere resultados. |
| Recursos limitados | Dimensionar el laboratorio y ejecutar escenarios controlados. |
| Dependencias incompatibles | Fijar versiones justificadas y validar en Windows 11 y el futuro Ubuntu Server. |
| Falta de tiempo | Priorizar reglas demostrables y criterios esenciales del MVP. |
| Pérdida de reproducibilidad | Versionar código, metadatos, ejemplos y documentación; registrar el entorno. |

## 20. Próxima acción oficial

Los Incrementos 6 y 7 están completados. El cierre del Incremento 7 fue fusionado mediante la Pull Request #8 y el merge commit `f405f57f46f2fc9e04b78ce529bfe974fa530f3d`; la suite alcanzó 265 pruebas aprobadas.

La próxima etapa oficial es el **Incremento 8 — Ampliación controlada del catálogo determinista de running-config**, aprobado y todavía no implementado. PostgreSQL, Streamlit, reportes, inteligencia artificial y demás alternativas posteriores permanecen fuera de su alcance y pendientes de evaluación.
