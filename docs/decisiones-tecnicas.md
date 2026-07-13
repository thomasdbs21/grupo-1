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
- pytest para las pruebas automatizadas.
- Reglas deterministas con lógica implementada en Python.
- YAML para los metadatos declarativos de las reglas.
- Streamlit como interfaz inicial del MVP, en un incremento posterior al primero.
- GNS3, GNS3 VM, Cisco IOSv e IOSvL2 para el laboratorio de validación.
- Windows 11 y VMware Workstation como plataforma anfitriona y de virtualización.

## Componentes futuros

Los siguientes componentes están aprobados para incrementos posteriores, pero no forman parte del primer incremento:

- TextFSM para analizar salidas de comandos `show`.
- Netmiko para conexiones SSH de solo lectura.
- FastAPI para exponer la API del sistema.
- PostgreSQL para la persistencia de datos.
- SQLAlchemy como ORM.
- Alembic para gestionar migraciones de base de datos.
- Streamlit para la interfaz inicial.
- Ubuntu Server como servidor del asistente.
- Una pasarela opcional de inteligencia artificial.

## Restricciones de seguridad

- El sistema será de solo lectura y no ingresará al modo de configuración de los dispositivos.
- No ejecutará cambios automáticos, comandos destructivos, reinicios ni operaciones de guardado sobre dispositivos.
- Las conexiones SSH futuras mediante Netmiko estarán limitadas a operaciones de consulta autorizadas.
- Las credenciales, contraseñas, claves privadas, tokens, claves API y demás secretos no se almacenarán en texto plano.
- Las credenciales y los secretos no aparecerán en logs, reportes, mensajes de error ni solicitudes enviadas a servicios de inteligencia artificial.
- Toda información enviada a la pasarela de inteligencia artificial deberá ser sanitizada previamente.
- La indisponibilidad de la inteligencia artificial no impedirá ejecutar el análisis técnico.

## Decisiones sobre reglas y hallazgos

- Las detecciones serán producidas exclusivamente por reglas deterministas.
- La lógica de evaluación de las reglas se implementará en Python y sus metadatos se almacenarán en YAML.
- Las reglas recibirán un contexto normalizado y no tendrán acceso directo a SSH, Netmiko, bases de datos ni inteligencia artificial.
- Las reglas no ejecutarán comandos en dispositivos ni modificarán el contexto recibido.
- `rule_evaluations` almacenará el resultado de todas las reglas evaluadas, independientemente de su estado.
- `findings` almacenará únicamente hallazgos derivados de evaluaciones con estado `FAIL`.
- Las evidencias conservarán, como mínimo, su origen, fecha de recopilación, contenido original, contenido normalizado, fragmento relevante, hash de integridad e identificador de ejecución.
- Cada hallazgo deberá estar vinculado con la regla determinista y la evidencia que justifican el resultado.

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

## Decisiones pendientes

Las siguientes decisiones deberán concretarse cuando se planifiquen los incrementos correspondientes:

- El esquema físico definitivo de PostgreSQL y las relaciones entre evaluaciones, hallazgos y evidencias.
- El contrato y versionado de la API FastAPI.
- La lista blanca definitiva de comandos permitidos mediante SSH.
- El formato de plantillas TextFSM y la estrategia de normalización de comandos `show`.
- El mecanismo de despliegue y operación en Ubuntu Server.
- El proveedor, modelo y política de retención de datos de la pasarela opcional de inteligencia artificial.
- El diseño definitivo de la interfaz Streamlit.

Estas decisiones pendientes no amplían el alcance del primer incremento y deberán documentarse antes de implementar cada componente futuro.
