# Decisiones técnicas

## Propósito

Este documento registra las decisiones técnicas oficiales actuales del proyecto. El sistema analizará configuraciones Cisco IOS para detectar errores, inconsistencias, riesgos, controles de seguridad ausentes y malas prácticas. Las detecciones se realizarán mediante reglas deterministas y deberán conservar evidencia suficiente para que sus resultados sean verificables y trazables.

El sistema será un asistente de análisis de solo lectura. No administrará dispositivos ni aplicará cambios automáticos sobre ellos.

## Decisiones oficiales

- El laboratorio se implementará en GNS3 con routers Cisco IOSv y switches Cisco IOSvL2.
- Windows 11 será el sistema anfitrión del entorno de desarrollo y laboratorio.
- VMware Workstation y GNS3 VM proporcionarán la virtualización del laboratorio.
- Ubuntu Server será, en un incremento posterior, el servidor del asistente.
- Python será el lenguaje principal del proyecto.
- `ciscoconfparse2` se utilizará para analizar archivos `running-config`; la clase importada continúa llamándose `CiscoConfParse`.
- El sistema conservará una separación explícita entre recopilación, parsing, normalización, reglas, almacenamiento, API, interfaz e inteligencia artificial.
- El sistema no realizará cambios automáticos sobre dispositivos Cisco IOS.

## Stack del MVP

- Python como lenguaje principal.
- `ciscoconfparse2`, mediante la clase `CiscoConfParse`, para el parsing de configuraciones `running-config`.
- Netmiko para la recopilación SSH de solo lectura desde Cisco IOS e IOS XE.
- pytest para las pruebas automatizadas.
- Reglas deterministas con lógica implementada en Python.
- YAML para los metadatos declarativos de las reglas.
- Streamlit como interfaz inicial del MVP, en un incremento posterior al primero.
- GNS3, GNS3 VM, Cisco IOSv e IOSvL2 para el laboratorio de validación.
- Windows 11 y VMware Workstation como plataforma anfitriona y de virtualización.

## Componentes futuros

Los siguientes componentes están aprobados para incrementos posteriores y todavía no están integrados en el flujo SSH completado:

- TextFSM para analizar salidas de comandos `show`.
- PostgreSQL para la persistencia de datos.
- SQLAlchemy como ORM.
- Alembic para gestionar migraciones de base de datos.
- Streamlit para la interfaz inicial.
- Ubuntu Server como servidor del asistente.
- Una pasarela opcional de inteligencia artificial.

## Restricciones de seguridad

- El sistema será de solo lectura y no ingresará al modo de configuración de los dispositivos.
- No ejecutará cambios automáticos, comandos destructivos, reinicios ni operaciones de guardado sobre dispositivos.
- Las conexiones SSH mediante Netmiko están limitadas a operaciones de consulta autorizadas.
- Las credenciales, contraseñas, claves privadas, tokens, claves API y demás secretos no se almacenarán en texto plano.
- Las credenciales y los secretos no aparecerán en logs, reportes, mensajes de error ni solicitudes enviadas a servicios de inteligencia artificial.
- Toda información enviada a la pasarela de inteligencia artificial deberá ser sanitizada previamente.
- La indisponibilidad de la inteligencia artificial no impedirá ejecutar el análisis técnico.

## Decisiones sobre SSH de solo lectura

- `NetmikoCollector` es el recolector oficial de solo lectura para Cisco IOS e IOS XE en el Incremento 4.
- La lista blanca es un `frozenset` inmutable con `show running-config`, `show version`, `show ip interface brief` y `show ip ssh`.
- Los comandos se normalizan antes de comparar, pero después deben coincidir exactamente con la lista blanca.
- Pipes, punto y coma, saltos de línea y argumentos adicionales se rechazan antes de abrir una conexión.
- Uno o varios comandos autorizados utilizan una única sesión y comparten un `execution_id`.
- Cada salida produce una `CommandEvidence` inmutable con fecha UTC, contenido original, contenido normalizado y SHA-256.
- Usuario, contraseña y fábrica de conexión se excluyen del `repr` del recolector; las salidas se excluyen del `repr` de la evidencia.
- La sesión se cierra mediante `disconnect()` incluso cuando ocurre un error durante la ejecución.
- Las excepciones de autenticación, timeout, conexión y contrato utilizan mensajes sanitizados.
- Se prohíbe utilizar `send_config_set()`, `config_mode()` o cualquier comando de configuración.
- El sistema continúa sin aplicar cambios automáticos sobre dispositivos.

## Decisiones sobre la integración SSH y el analizador

- `RunningConfigCollector` define el protocolo mínimo entre el orquestador y cualquier recolector compatible; no almacena credenciales ni depende de la implementación concreta.
- `analyze_collected_running_config()` es el orquestador separado para integrar `show running-config` con el analizador en memoria.
- El orquestador solicita un único comando exacto, valida cardinalidad, tipo de evidencia, comando, UUID e integridad, y no crea archivos temporales.
- `CommandEvidence.sha256` se calcula sobre `raw_output.encode("utf-8")`.
- `analyze_bytes()` recibe esos mismos bytes para que `AnalysisResult.sha256` coincida con el hash de la evidencia.
- `parse_running_config()` normaliza después el contenido y construye el `AnalysisContext` inmutable.
- `normalized_output` permanece en la evidencia para trazabilidad, pero no reemplaza la salida original analizada.
- `CollectedAnalysisResult` conserva juntos la evidencia y el resultado sin almacenar el recolector ni copiar las salidas.
- Las reglas continúan recibiendo únicamente `AnalysisContext`; no conocen Netmiko, SSH, credenciales, FastAPI, repositorios, base de datos ni inteligencia artificial.
- La integración SSH no está expuesta mediante FastAPI y no tiene persistencia en esta etapa.

## Decisiones sobre reglas y hallazgos

- Las detecciones serán producidas exclusivamente por reglas deterministas.
- La lógica de evaluación de las reglas se implementará en Python y sus metadatos se almacenarán en YAML.
- Las reglas recibirán un contexto normalizado y no tendrán acceso directo a SSH, Netmiko, bases de datos ni inteligencia artificial.
- Las reglas no ejecutarán comandos en dispositivos ni modificarán el contexto recibido.
- `rule_evaluations` almacenará el resultado de todas las reglas evaluadas, independientemente de su estado.
- `findings` almacenará únicamente hallazgos derivados de evaluaciones con estado `FAIL`.
- Las evidencias conservarán, como mínimo, su origen, fecha de recopilación, contenido original, contenido normalizado, fragmento relevante, hash de integridad e identificador de ejecución.
- Cada hallazgo deberá estar vinculado con la regla determinista y la evidencia que justifican el resultado.
- Los metadatos oficiales de cada regla se almacenarán en un YAML independiente y versionado.
- Los YAML no contendrán condiciones ni lógica de detección; la evaluación permanecerá exclusivamente en Python.
- La carga utilizará `yaml.safe_load` y se limitará a archivos esperados dentro de los recursos del paquete.
- `RuleMetadata` será inmutable y el registro rechazará campos inválidos, versiones vacías, severidades desconocidas, IDs duplicados o asociaciones inconsistentes.
- Un `RuleRegistry` central mantendrá el orden determinista, permitirá consulta por ID y ejecutará únicamente reglas habilitadas.

## Decisiones sobre la API local

- FastAPI y Uvicorn implementan la API del Incremento 3 sin incorporar lógica técnica de reglas.
- La API procesa archivos multipart en memoria, acepta `.cfg`, `.conf` y `.txt` y limita cada carga a 2 MiB.
- Se acepta UTF-8 y UTF-8 con BOM; los binarios, archivos vacíos y codificaciones inválidas se rechazan.
- Los nombres se sanitizan a su componente base y nunca se utilizan rutas proporcionadas por el cliente.
- Las respuestas no incluyen rutas absolutas, configuraciones completas ni secretos sin redactar.
- Cada análisis síncrono completado recibe un UUID y se guarda temporalmente en memoria.
- El repositorio es seguro para concurrencia básica, conserva como máximo 100 análisis y elimina el más antiguo al superar el límite.
- El almacenamiento se pierde al reiniciar y será reemplazado por PostgreSQL en el Incremento 6.
- Solo existe el estado de ejecución `COMPLETED`; no se implementan tareas pendientes, workers ni colas.

## Decisiones sobre inteligencia artificial

- La pasarela de inteligencia artificial será opcional e independiente del motor de reglas.
- La inteligencia artificial solo explicará, resumirá y priorizará hallazgos previamente detectados y validados.
- La priorización respetará los estados, severidades y criterios definidos por las reglas.
- La inteligencia artificial no decidirá si una configuración cumple o incumple una regla.
- La inteligencia artificial no inventará hallazgos, reglas ni evidencias.
- La inteligencia artificial no alterará resultados, severidades, recomendaciones validadas ni evidencias.
- La inteligencia artificial no recibirá credenciales ni información sensible sin sanitización.

## Alcance del primer incremento

El primer incremento analizará únicamente archivos locales `running-config` e incluirá:

- Lectura y validación básica de archivos locales.
- Conservación del contenido original y cálculo de su hash.
- Parsing mediante `ciscoconfparse2`, usando la clase `CiscoConfParse`.
- Construcción de un contexto normalizado.
- Ejecución de tres reglas piloto deterministas.
- Registro de las evaluaciones y creación de hallazgos solamente para resultados `FAIL`.
- Salida estructurada y pruebas automatizadas con pytest.

Quedan expresamente fuera del primer incremento:

- SSH y Netmiko.
- PostgreSQL, SQLAlchemy y Alembic.
- FastAPI.
- Streamlit.
- TextFSM y el análisis de comandos `show`.
- La pasarela de inteligencia artificial.

## Alcance completado del Incremento 4

El Incremento 4 incorpora el recolector Netmiko de solo lectura y su integración con el analizador determinista para `show running-config`. Incluye lista blanca, evidencias inmutables, cierre seguro, excepciones sanitizadas, protocolo desacoplado, verificación de hashes y pruebas sin red.

La validación automatizada alcanzó 78 pruebas después del recolector y 96 después de la integración. Además, se realizaron validaciones manuales controladas del recolector y del flujo integrado contra un CSR1000v IOS XE 16.9.5 ejecutado en VirtualBox, sin conservar configuración ni información sensible en la documentación.

Permanecen fuera de este incremento el parsing TextFSM de los otros comandos `show`, la persistencia PostgreSQL, la exposición SSH mediante FastAPI y la integración con inteligencia artificial.

## Decisiones pendientes

Las siguientes decisiones deberán concretarse cuando se planifiquen los incrementos correspondientes:

- El esquema físico definitivo de PostgreSQL y las relaciones entre evaluaciones, hallazgos y evidencias.
- La evolución del contrato más allá de `/api/v1`.
- La eventual ampliación controlada de la lista blanca para incrementos posteriores.
- El formato de plantillas TextFSM y la estrategia de normalización de comandos `show`.
- El mecanismo de despliegue y operación en Ubuntu Server.
- El proveedor, modelo y política de retención de datos de la pasarela opcional de inteligencia artificial.
- El diseño definitivo de la interfaz Streamlit.

Estas decisiones pendientes no amplían el alcance del primer incremento y deberán documentarse antes de implementar cada componente futuro.
