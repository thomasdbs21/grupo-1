# Definición del Incremento 9: persistencia relacional del análisis integral

## 1. Identificación

| Elemento | Definición |
|---|---|
| Nombre oficial | Incremento 9 — Persistencia relacional del análisis integral |
| Estado | APROBADO Y PLANIFICADO; NO IMPLEMENTADO |
| Base funcional | `main` en `99e0b8c5519c544b0d3dde389f2c0690078c4b3d` |
| Tecnologías previstas | PostgreSQL, SQLAlchemy y Alembic |
| Corte seleccionado | Opción B: esquema, migración, puerto, adaptador y servicio programático |
| Integración HTTP | Fuera del incremento |

Este documento autoriza únicamente el alcance aquí definido. No demuestra que existan dependencias, tablas, migraciones, una base de datos ni código de persistencia.

## 2. Situación inicial

El proyecto ya dispone de:

- `FullDeviceAnalysisResult` inmutable, con un `execution_id`, cuatro `CommandEvidence`, un `AnalysisResult`, tres `OperationalContext`, todas las evaluaciones y los findings;
- exactamente ocho evaluaciones en el flujo integral vigente: siete de `running-config` y `IOS-IF-001`;
- `Finding` derivado exactamente de cada `RuleEvaluation` con estado `FAIL`;
- cuatro comandos canónicos y evidencias con fecha UTC y SHA-256;
- una respuesta HTTP integral explícita y sanitizada;
- un repositorio en memoria para análisis de archivos, limitado a 100 elementos y perdido al terminar el proceso;
- 314 pruebas aprobadas al cierre del Incremento 8.

No existen PostgreSQL, SQLAlchemy, Alembic, driver de PostgreSQL, configuración de base de datos, modelos relacionales ni pruebas de infraestructura declarados en `pyproject.toml`, `src/` o `tests/`. Tampoco existe todavía un `analysis_id` para el resultado integral: su único identificador estable actual es `execution_id`.

## 3. Problema

El resultado integral solo vive en memoria durante la solicitud. No puede recuperarse después de reiniciar el proceso, no existe una transacción que conserve conjuntamente sus evidencias y resultados, y no hay una representación histórica consultable por UUID.

Persistir directamente `FullDeviceAnalysisResult` sería inseguro e incorrecto: contiene host del dispositivo, `raw_output`, `normalized_output`, configuración completa, rutas o fuentes, nombres y direcciones de interfaces y contextos operacionales detallados. Además, `RuleEvaluation` no conserva la versión de la regla y `Finding` no contiene el riesgo de sus metadatos.

## 4. Objetivo

Implementar, en una etapa posterior a esta definición, el menor corte funcional capaz de:

1. crear un esquema PostgreSQL versionado;
2. transformar un resultado integral ya completado en una proyección persistente sanitizada;
3. guardar esa proyección en una única transacción;
4. conservar todas las evaluaciones en su orden;
5. conservar un finding únicamente por cada evaluación `FAIL`;
6. recuperar programáticamente una representación persistente equivalente mediante `analysis_id` o `execution_id`;
7. mantener el dominio y las reglas independientes de SQLAlchemy.

La equivalencia persistente significa conservar resultados técnicos y trazabilidad autorizada. No significa reconstruir salidas completas, contextos operacionales ni el objeto de dominio original byte por byte.

## 5. Alcance

El Incremento 9 incluirá:

- dependencias mínimas y compatibles de SQLAlchemy, Alembic y un driver PostgreSQL;
- configuración externa y validada de la URL de conexión;
- modelos SQLAlchemy ubicados solo en infraestructura;
- una migración inicial reproducible desde una base vacía;
- un puerto de persistencia definido en la capa de aplicación;
- un adaptador PostgreSQL mediante SQLAlchemy;
- modelos de transferencia inmutables para la proyección persistente;
- un servicio que valide, sanitice, enriquezca y persista un `FullDeviceAnalysisResult` ya completado;
- consulta programática por `analysis_id` y `execution_id`;
- una transacción atómica por análisis;
- pruebas unitarias sin base de datos y pruebas de integración contra PostgreSQL real;
- documentación de implementación y operación mínima.

## 6. Fuera del alcance

No se incluirán:

- persistencia automática desde `POST /api/v1/device-analyses`;
- cambios en endpoints existentes o endpoints históricos nuevos;
- persistencia de análisis de archivos del repositorio temporal;
- reemplazo del repositorio en memoria de FastAPI;
- tareas asíncronas, colas, workers o estados parciales;
- retención, borrado, archivado o anonimización masiva;
- cifrado de columnas o gestión de claves;
- autenticación o autorización de usuarios;
- Streamlit, reportes, inteligencia artificial o nuevas reglas;
- cambios en SSH, Netmiko, parsers, comandos o dispositivos;
- alta disponibilidad, replicación, copias de seguridad o despliegue productivo;
- almacenamiento de salidas completas o configuraciones.

## 7. Decisiones técnicas

### 7.1 Corte vertical seleccionado

Se selecciona la **opción B**. La opción A dejaría infraestructura sin demostrar que el agregado real puede persistirse de forma coherente. La opción B agrega el mínimo valor comprobable: escritura atómica y lectura programática de una auditoría integral sanitizada.

Las opciones C y D se posponen. Integrar el `POST` cambiaría su disponibilidad, latencia, errores y semántica transaccional. Exponer historial exigiría antes definir autorización, paginación, retención y contrato público.

### 7.2 Dependencias

El dominio, las reglas, los parsers y los collectors no importarán SQLAlchemy. El puerto y los DTO persistentes pertenecerán a aplicación; SQLAlchemy, el motor y las sesiones síncronas pertenecerán a infraestructura. Alembic será el único mecanismo oficial para evolucionar el esquema y no se ejecutará automáticamente al iniciar FastAPI.

Las sesiones SQLAlchemy síncronas forman parte del alcance aprobado. La aplicación, Netmiko, `collect_and_analyze_device()` y los servicios actuales son síncronos; el corte no integra FastAPI ni introduce colas, trabajos en segundo plano o procesamiento asíncrono. `AsyncSession` queda fuera del alcance porque agregaría complejidad sin valor funcional comprobable. Una posible evolución asíncrona deberá aprobarse posteriormente como cambio arquitectónico.

El repositorio no aporta todavía una base suficiente para aprobar:

- versión o rango de SQLAlchemy;
- driver PostgreSQL ni su distribución;
- PostgreSQL de pruebas mediante contenedor, servicio de CI o instancia administrada;
- configuración del pool de producción.

Esta definición no instala ni declara SQLAlchemy, un driver o PostgreSQL y no resuelve esas decisiones pendientes.

### 7.3 Representación equivalente

No se serializará `FullDeviceAnalysisResult` de forma genérica ni se prometerá reconstruirlo. El contrato histórico reconstruible se denominará conceptualmente `PersistedDeviceAnalysis` y contendrá:

- `analysis_id`;
- `execution_id`;
- `DeviceIdentity`, con alias lógico y plataforma genérica opcional;
- `origin=INTEGRAL_DEVICE_ANALYSIS`;
- `persisted_at` en UTC;
- cuatro `PersistedCommandEvidence` ordenadas, con ID, comando, ordinal, `collected_at` y SHA-256;
- todas las `PersistedRuleEvaluation` ordenadas, con snapshot técnico y evidencia autorizada;
- un `PersistedFinding` por cada evaluación `FAIL`, proyectado desde la evaluación relacionada.

Cada `PersistedRuleEvaluation` conservará `evaluation_id`, `rule_id`, `rule_version`, `rule_name`, estado, severidad, mensaje, recomendación, riesgo, ordinal y una colección ordenada de evidencia autorizada. Cada `PersistedFinding` expondrá `finding_id`, `evaluation_id` y, mediante la proyección de consulta, ID de regla, severidad, mensaje, recomendación, riesgo y evidencia de la evaluación.

`PersistedDeviceAnalysis` excluirá `raw_output`, `normalized_output`, `AnalysisContext`, `OperationalContext`, `AnalysisResult`, configuración completa, host de administración, credenciales, rutas, direcciones, objetos Netmiko y cualquier dato no autorizado. Es una vista histórica del resultado técnico, no un objeto apto para reejecutar parsers o reglas.

### 7.4 Versiones y riesgo

`RuleEvaluation` no contiene `rule_version` y `Finding` no contiene `risk`. Un componente de aplicación denominado conceptualmente `AnalysisSnapshotBuilder` recibirá el resultado integral, `DeviceIdentity` y un `RuleMetadataResolver` inyectado. El resolver reunirá los metadatos oficiales del `RuleRegistry` de configuración y del cargador separado de `IOS-IF-001`.

El builder, no el adaptador SQLAlchemy:

- buscará cada evaluación por `rule_id`;
- validará que no falten metadatos ni existan IDs duplicados;
- comprobará la coherencia de nombre, severidad y recomendación con la definición oficial;
- copiará como snapshot `rule_id`, versión, nombre, estado, severidad, mensaje, recomendación y riesgo;
- construirá `PersistedDeviceAnalysis` antes de abrir la transacción.

Las consultas históricas leerán esos snapshots y no volverán a cargar el YAML vigente. El adaptador SQLAlchemy solo mapeará el contrato ya validado y no importará `RuleRegistry`, no resolverá metadatos ni decidirá contenido técnico.

### 7.5 Identidad del dispositivo

El servicio programático recibirá obligatoriamente un `DeviceIdentity` independiente de `FullDeviceAnalysisResult`:

- `logical_alias`: alias canónico obligatorio;
- `platform`: `CISCO_IOS` o `CISCO_IOS_XE`, opcional; si no puede declararse sin inferir datos sensibles, se utilizará `None`.

El alias será proporcionado explícitamente por el consumidor de aplicación. No se inferirá desde `device_host`, IP, hostname, hash, plataforma, salida de comandos ni ningún otro dato del resultado. El endpoint HTTP no se modificará para solicitarlo.

El contrato inicial aceptará únicamente alias que cumplan `^[a-z0-9][a-z0-9_-]{0,63}$`. No realizará correcciones silenciosas: espacios, puntos, dos puntos, barras, `@`, mayúsculas y valores con forma de dirección serán rechazados. Varias ejecuciones se asociarán al mismo `Device` solo cuando el consumidor entregue exactamente el mismo alias canónico. Si el alias falta o es inválido, el builder rechazará la operación antes de invocar el puerto. No habrá deduplicación automática.

## 8. Diseño de capas

```text
FullDeviceAnalysisResult + DeviceIdentity
                         |
                         v
AnalysisSnapshotBuilder
  - valida contrato integral
  - resuelve metadatos de reglas
  - sanitiza evidencia
  - crea PersistedDeviceAnalysis
                         |
                         v
AnalysisPersistencePort
  - save()
  - get_by_analysis_id()
  - get_by_execution_id()
                         |
                         v
adaptador SQLAlchemy / unidad de trabajo
                         |
                         v
PostgreSQL + esquema administrado por Alembic
```

Las reglas no conocerán el puerto. El servicio de persistencia recibirá un resultado ya producido; no abrirá SSH, no volverá a analizar y no ejecutará reglas. La capa de aplicación generará `analysis_id`, construirá el snapshot y entregará al puerto un contrato independiente de SQLAlchemy.

## 9. Modelo relacional propuesto

El modelo físico definitivo se confirmará durante la implementación mediante la migración revisada. La propuesta mínima es:

### `devices`

- `device_id`: UUID, clave primaria;
- `logical_alias`: alias canónico, obligatorio y único;
- `platform`: valor genérico controlado y opcional, sin versión ni hostname;
- `created_at`, `updated_at`: fechas UTC.

El servicio resolverá o creará `Device` por coincidencia exacta de `logical_alias`. La plataforma no participará en la deduplicación. No se derivará el alias desde `device_host` ni se creará un dispositivo anónimo cuando falte.

### `analysis_runs`

- `analysis_id`: UUID, clave primaria generada para persistencia;
- `execution_id`: UUID único proveniente del resultado integral;
- `device_id`: clave foránea;
- `origin`: valor controlado `INTEGRAL_DEVICE_ANALYSIS`;
- `persisted_at`: fecha UTC generada por aplicación inmediatamente antes de abrir la transacción.

No se almacenará `status`: la existencia de la fila representa un resultado integral completo ya construido. Tampoco se inventará `executed_at`, porque el contrato actual solo aporta las fechas de recopilación de cada evidencia. Los conteos se calcularán desde relaciones para evitar duplicación y deriva. Estados `PENDING`, `RUNNING` o `FAILED` quedan fuera del incremento.

### `command_evidences`

- `evidence_id`: UUID, clave primaria;
- `analysis_id`: clave foránea;
- `command`: uno de los cuatro comandos canónicos;
- `ordinal`: orden canónico;
- `collected_at`: fecha UTC;
- `sha256`: 64 caracteres hexadecimales minúsculos.

No tendrá columnas para host, salida original, salida normalizada o configuración.

### `rule_evaluations`

- `evaluation_id`: UUID, clave primaria;
- `analysis_id`: clave foránea;
- `rule_id`, `rule_version`, `rule_name`;
- `status`, `severity`;
- `message`, `recommendation`, `risk`;
- `ordinal`: orden original de la evaluación.

La tabla no fijará la cardinalidad en ocho para permitir crecimiento del catálogo, pero exigirá IDs y ordinales únicos dentro del análisis.

### `evaluation_evidences`

- `evaluation_evidence_id`: UUID, clave primaria;
- `evaluation_id`: clave foránea;
- `command_evidence_id`: clave foránea a la evidencia canónica que constituye la fuente técnica de la regla;
- `line_number`: opcional y positivo;
- `content`: fragmento controlado o evidencia sintética sanitizada;
- `ordinal`: orden dentro de la evaluación.

La tabla es necesaria para conservar cardinalidad, orden y trazabilidad de cero, uno o varios fragmentos sin duplicar columnas en `rule_evaluations`. La relación se decidirá en `AnalysisSnapshotBuilder` según la fuente oficial de la regla: las siete reglas de configuración se vinculan a `show running-config` e `IOS-IF-001` a `show ip interface brief`. No se inferirá la relación únicamente por hash.

El SHA-256 almacenado en `command_evidences` seguirá siendo el hash del `raw_output` original. La coincidencia entre `Evidence.sha256` y ese hash será una comprobación de consistencia del contrato, pero no demostrará que el fragmento sanitizado pertenecía literalmente a la salida. Como el contenido original no se guarda, esa pertenencia no podrá verificarse posteriormente. No se añadirá un hash propio del fragmento en este incremento porque no aporta una garantía adicional útil sobre su origen.

### `findings`

- `finding_id`: UUID, clave primaria;
- `evaluation_id`: clave foránea única.

El análisis, la severidad, el mensaje, la recomendación, el riesgo y la evidencia se consultarán mediante el snapshot de evaluación relacionado para evitar claves o copias divergentes. Solo una evaluación `FAIL` podrá tener finding; toda evaluación `FAIL` deberá tener exactamente uno.

## 10. Relaciones y cardinalidades

- `Device 1:N AnalysisRun`.
- `AnalysisRun 1:4 CommandEvidence` para el contrato integral vigente.
- `AnalysisRun 1:N RuleEvaluation`; actualmente son ocho, sin fijarlo en el esquema.
- `RuleEvaluation 0:N EvaluationEvidence`.
- `CommandEvidence 1:N EvaluationEvidence`.
- `RuleEvaluation 0:1 Finding`.
- `AnalysisRun 0:N Finding`, siempre como proyección de sus evaluaciones `FAIL`.

Las restricciones SQL cubrirán claves, unicidad, formatos básicos y relaciones. Las invariantes que cruzan varias filas —cuatro comandos exactos y finding si y solo si `FAIL`— se validarán en el servicio dentro de la transacción y en pruebas. No se usarán triggers en este incremento.

No habrá operaciones de borrado en el Incremento 9. Las claves foráneas usarán `ON DELETE RESTRICT` y la migración inicial no incorporará borrado en cascada. Una política futura de retención deberá justificar su semántica y agregarla mediante otra migración.

### Responsabilidades de garantía

| Capa | Garantías |
|---|---|
| Dominio actual | Inmutabilidad del resultado; findings iguales a la proyección de evaluaciones `FAIL`; lote integral ya validado por los servicios existentes |
| `AnalysisSnapshotBuilder` | `DeviceIdentity`, UUID, metadata snapshot, fuente de cada regla, sanitización, cuatro evidencias, orden, UTC, comandos, hashes y correspondencia exacta `FAIL`–finding |
| `AnalysisPersistencePort` | Semántica de guardar una vez, consultar por ambos UUID, conflicto por duplicado y ausencia de resultados parciales |
| Adaptador SQLAlchemy | Mapeo sin decisiones técnicas, una transacción, rollback, traducción de errores y reconstrucción del DTO histórico |
| PostgreSQL | Claves primarias y foráneas, unicidad, `NOT NULL`, checks locales, ordinales, enums controlados y `ON DELETE RESTRICT` |
| Pruebas | Comportamiento conjunto, migración, restricciones reales, fallos intermedios, rollback, sanitización y ausencia de deriva |

PostgreSQL no puede garantizar por sí solo, sin triggers ni lógica adicional, que existan exactamente los cuatro comandos canónicos, que todo `FAIL` tenga finding o que ninguna evaluación de otro estado lo tenga. Esas invariantes pertenecen al dominio y al servicio, con respaldo de pruebas; la base solo impedirá duplicados, referencias inválidas y valores locales fuera de contrato.

## 11. Política de identificadores

- `execution_id` conserva el UUID generado antes de la recopilación y es único en la base.
- `analysis_id` es un UUID nuevo generado por la capa de aplicación antes de invocar el puerto y será la clave primaria de consulta.
- `device_id`, `evidence_id`, `evaluation_id`, `evaluation_evidence_id` y `finding_id` serán UUID internos.
- Ambos identificadores serán únicos y la consulta programática admitirá cualquiera.
- Reintentar el mismo `execution_id`, aun con el mismo contenido, producirá un conflicto seguro y no escribirá parcialmente. El Incremento 9 no define una operación idempotente de creación.
- Tras una respuesta incierta del almacenamiento, el consumidor deberá consultar por `execution_id` antes de intentar una nueva persistencia. Convertir esa secuencia en idempotencia automática queda para una decisión posterior.
- `FullDeviceAnalysisResult` no se modificará para incorporar `analysis_id`.
- Los IDs de reglas continúan siendo los identificadores textuales oficiales.
- Los UUID no contendrán significado de red y no se derivarán de datos sensibles.

## 12. Política de evidencia

En el Incremento 9:

- `raw_output` **no se persiste**;
- `normalized_output` **no se persiste**;
- `running-config` completo **no se persiste**;
- `AnalysisContext`, `OperationalContext` y objetos Netmiko **no se persisten**;
- `device_host`, `source_path`, nombres de host, direcciones de interfaces, destinos NTP o Syslog y números de serie **no se persisten**;
- se persisten comando, fecha UTC y SHA-256 de cada evidencia canónica;
- se persiste solo evidencia de regla mínima tras una transformación autorizada.

Los fragmentos no se aceptarán como texto libre desde consumidores externos. `AnalysisSnapshotBuilder` aplicará una política por regla y conservará únicamente directivas ya redactadas o textos sintéticos aprobados. Un fragmento que no cumpla su política causará rechazo antes de invocar el puerto.

Para `IOS-IF-001` se selecciona la alternativa A: persistir por cada inconsistencia una descripción controlada y genérica, por ejemplo `interfaz activa: status up, protocol down`, sin nombre, dirección ni pseudónimo de interfaz. Esto conserva la condición técnica y la cantidad de inconsistencias, pero no permite identificar la interfaz concreta. La limitación es deliberada; la pseudonimización estable y la persistencia del nombre original quedan fuera de este incremento.

El SHA-256 canónico aporta integridad de la salida mientras esta existe en el flujo y correlación histórica, no confidencialidad ni prueba de pertenencia literal del fragmento. No autoriza conservar ni exponer la salida que originó el hash.

## 13. Política de información sensible

- Credenciales, usuario SSH, contraseña, host y puerto de conexión nunca entrarán al puerto ni a las tablas.
- La URL de base de datos se obtendrá de configuración externa y nunca se incluirá completa en logs, errores o representaciones.
- No se almacenarán cadenas de conexión, objetos de sesión, motores SQLAlchemy ni errores del driver como datos del dominio.
- Los mensajes y riesgos persistidos provendrán de reglas y metadatos oficiales, no de excepciones ni entradas arbitrarias.
- Los aliases de dispositivo serán lógicos y sanitizados; no se inferirán del destino real.
- Las pruebas usarán datos sintéticos y buscarán marcadores secretos en filas, errores y logs.
- La persistencia no modifica dispositivos ni amplía la lista blanca.

## 14. Transacciones

Cada análisis se guardará en una única transacción:

1. validar completamente la entrada y construir la proyección fuera de la sesión;
2. iniciar la unidad de trabajo;
3. resolver o crear el dispositivo por alias;
4. insertar `AnalysisRun`;
5. insertar cuatro `CommandEvidence`;
6. insertar todas las evaluaciones y su evidencia autorizada;
7. insertar un finding por cada `FAIL`;
8. verificar conteos e invariantes;
9. confirmar una sola vez.

Cualquier error ejecutará rollback. El servicio no devolverá un éxito antes del commit y no dejará dispositivo, ejecución, evidencia, evaluación o finding parcial. El adaptador no realizará commits internos por entidad.

## 15. Migraciones

- Alembic será la única fuente de evolución del esquema.
- La primera revisión creará tipos, tablas, restricciones, índices y claves foráneas desde una base vacía.
- La aplicación no usará `metadata.create_all()` en ejecución normal.
- `alembic upgrade head` deberá funcionar en PostgreSQL vacío.
- La migración inicial tendrá un `downgrade` revisado para el entorno de desarrollo; no autoriza borrado en producción.
- No habrá migración automática al iniciar FastAPI.
- La revisión deberá comparar metadatos y migración para detectar deriva.

## 16. Configuración

La aplicación no tiene hoy un sistema de settings. El incremento añadirá una configuración mínima en el límite de composición:

- la variable externa obligatoria `IOS_AUDITOR_DATABASE_URL` para la URL PostgreSQL;
- lectura diferida al construir la infraestructura, nunca al importar dominio o reglas;
- validación de esquema PostgreSQL y ausencia de valor vacío;
- mensajes seguros ante configuración ausente o inválida;
- configuración mínima para desarrollo y pruebas, sin definir todavía el pool de producción;
- archivo `.env.example` opcional con un valor ficticio sin credenciales reales.

No se incorporará una dependencia adicional de carga de `.env` salvo decisión separada. No se fijarán versiones exactas de paquetes hasta verificarlas durante la implementación.

## 17. Manejo de errores

La capa de aplicación expondrá errores propios y seguros, por ejemplo:

- configuración no disponible;
- contrato persistente inválido;
- análisis duplicado;
- almacenamiento no disponible;
- transacción fallida;
- análisis no encontrado.

El adaptador capturará excepciones específicas de SQLAlchemy y del driver, ejecutará rollback y evitará propagar URL, SQL con parámetros, credenciales, nombres internos o valores de entrada. Los errores inesperados conservarán su causa solo para manejo interno controlado; el texto público será constante y sanitizado.

Como el Incremento 9 no modifica FastAPI, todavía no se asignarán códigos HTTP a estos errores.

## 18. Estrategia de pruebas

### Pruebas unitarias sin base de datos

- proyección de un resultado integral válido;
- enriquecimiento de versión y riesgo desde metadatos;
- `DeviceIdentity` obligatorio, alias canónico, plataforma opcional y rechazo de cualquier inferencia desde `device_host`;
- cuatro comandos, hashes, UTC y `execution_id`;
- generación y unicidad contractual de `analysis_id`;
- `origin=INTEGRAL_DEVICE_ANALYSIS`, ausencia de `status` y `persisted_at` UTC;
- orden de evaluaciones;
- los cinco estados posibles;
- todas las evaluaciones preservadas;
- findings exclusivamente desde `FAIL`;
- rechazo de findings ausentes, adicionales o asociados a otros estados;
- resolución explícita entre regla y evidencia canónica, sin tratar el hash como prueba de pertenencia;
- sanitización genérica de `IOS-IF-001` sin nombre ni pseudónimo de interfaz;
- reconstrucción exacta de `PersistedDeviceAnalysis`, no de `FullDeviceAnalysisResult`;
- consultas históricas independientes de cambios posteriores en YAML;
- ausencia de credenciales, host, salidas y configuración;
- errores seguros;
- interacción única con un puerto falso;
- compatibilidad con ocho y futuras evaluaciones.

### Pruebas de integración con PostgreSQL real

- `alembic upgrade head` desde una base vacía;
- creación y consulta por ambos UUID;
- relaciones, restricciones e índices;
- cardinalidad de cuatro evidencias;
- persistencia y reconstrucción equivalente;
- conflicto por `execution_id` duplicado;
- hashes inválidos, fechas no UTC, comandos no autorizados y datos faltantes;
- checks locales, claves únicas, claves foráneas y `ON DELETE RESTRICT`;
- atomicidad ante fallos en distintas etapas;
- rollback sin filas huérfanas;
- integridad referencial;
- errores del adaptador sanitizados;
- migración y metadatos sin deriva.

PostgreSQL real será obligatorio para validar UUID, restricciones, transacciones y migraciones oficiales. Continúa pendiente de aprobación si se proporcionará mediante contenedor efímero, servicio PostgreSQL de CI o instancia administrada de pruebas. SQLite no será sustituto de estas pruebas; si se usa para pruebas auxiliares de mapeo, esas pruebas no contarán como validación del adaptador PostgreSQL.

Las pruebas no abrirán SSH, no iniciarán Uvicorn y no usarán el dispositivo real.

## 19. Criterios de aceptación

El incremento podrá cerrarse solo si:

1. el dominio y las reglas no importan SQLAlchemy;
2. la migración inicial se aplica en PostgreSQL vacío;
3. un resultado integral válido se guarda y `PersistedDeviceAnalysis` se recupera por cualquiera de los dos UUID;
4. la lectura devuelve el DTO histórico definido y no promete reconstruir `FullDeviceAnalysisResult`;
5. existen cuatro evidencias canónicas con UUID común, UTC y hashes válidos;
6. todas las evaluaciones conservan orden, estado y versión;
7. cada `FAIL` tiene exactamente un finding y ningún otro estado lo tiene;
8. un fallo produce rollback total;
9. duplicados e invariantes inválidas se rechazan sin filas parciales;
10. no se persisten credenciales, host, salidas, configuración completa ni contextos;
11. errores y logs no filtran URL ni secretos;
12. la suite anterior y las nuevas pruebas quedan aprobadas;
13. no cambian endpoints, SSH, comandos ni reglas;
14. documentación, esquema y código coinciden;
15. las consultas históricas no dependen del YAML vigente.

## 20. Riesgos

| Riesgo | Control propuesto |
|---|---|
| Persistir datos sensibles por serialización genérica | Proyección explícita y lista de campos permitidos |
| Perder versión o riesgo de la regla | Instantánea desde metadatos oficiales |
| Duplicar findings y evaluaciones | Claves únicas, servicio validado y una transacción |
| Deriva entre migración y modelos | Prueba de migración y comparación de metadatos |
| Diferencias SQLite/PostgreSQL | Integración obligatoria con PostgreSQL real |
| Duplicar una ejecución tras un reintento | `execution_id` único y conflicto seguro |
| Filtrar URL o parámetros SQL | Excepciones propias, logs constantes y pruebas con marcadores |
| Acoplar reglas a infraestructura | Puerto en aplicación y adaptador en infraestructura |
| Alias que reproduzca un hostname real | Contrato restrictivo y provisión explícita |
| Evidencia futura no contemplada | Rechazo seguro hasta aprobar una política de transformación |
| Interpretar el hash como prueba del fragmento | FK de fuente explícita y limitación documental de verificabilidad |

## 21. Limitaciones

- La persistencia se invocará solo programáticamente; el endpoint integral seguirá sin guardar resultados.
- El repositorio en memoria de análisis de archivos permanecerá separado.
- Solo se aceptarán resultados integrales ya completos; no existirá una columna `status` en esta etapa.
- No habrá búsquedas, listados, filtros, paginación ni API histórica.
- No se conservarán salidas suficientes para reconstruir `OperationalContext` o volver a ejecutar parsers.
- El alias sanitizado deberá ser suministrado por el consumidor; el resultado integral no contiene una identidad lógica segura.
- La política inicial de evidencia estará limitada a las ocho reglas vigentes.
- No podrá comprobarse posteriormente que un fragmento textual pertenecía literalmente al `raw_output` no almacenado.
- La versión o rango de SQLAlchemy, la provisión de PostgreSQL de pruebas, la selección y distribución del driver y el pool de producción continúan pendientes de aprobación.

## 22. Archivos previstos

Los nombres podrán ajustarse durante la implementación sin cambiar responsabilidades:

| Archivo o grupo | Responsabilidad prevista |
|---|---|
| `pyproject.toml` | Dependencias mínimas de persistencia y grupos de prueba |
| `.env.example` | Nombre de variable y ejemplo ficticio, si se aprueba |
| `src/ios_auditor/config.py` | Configuración externa validada |
| `src/ios_auditor/services/persistence.py` | `DeviceIdentity`, `PersistedDeviceAnalysis`, resolver de metadatos, builder, puerto y servicio de aplicación |
| `src/ios_auditor/infrastructure/persistence/` | Motor, sesiones síncronas, modelos y adaptador SQLAlchemy |
| `alembic.ini` y `migrations/` | Configuración y migración inicial |
| `tests/unit/test_persistence_service.py` | Contrato, sanitización e invariantes |
| `tests/integration/test_postgresql_persistence.py` | Adaptador, transacciones y consultas |
| documentos CORE y registro del incremento | Decisiones y evidencia de cierre |

No se prevén cambios en collectors, parsers, reglas, comandos, DTO HTTP o endpoints.

## 23. Secuencia de implementación

1. Crear la rama solo después de autorización.
2. Confirmar dependencias y estrategia PostgreSQL de pruebas.
3. Implementar contratos persistentes, política de sanitización y puerto.
4. Probar el servicio con un puerto falso.
5. Incorporar configuración, motor y sesiones.
6. Definir modelos SQLAlchemy y restricciones.
7. Crear y revisar la migración inicial.
8. Implementar el adaptador y la unidad de trabajo.
9. Probar escritura, lectura, conflictos y rollback contra PostgreSQL.
10. Ejecutar suite completa y auditorías de secretos.
11. Realizar cierre documental separado.

Cada bloque deberá poder revisarse y confirmarse con commits por propósito. No se usará `git add .`.

## 24. Próxima etapa

La integración con `POST /api/v1/device-analyses` es la candidata natural posterior, pero no queda numerada ni aprobada por este documento. Antes deberá decidirse si un fallo de base de datos hace fallar la solicitud, cómo se comunica el `analysis_id`, qué política de reintento existe y quién puede consultar historial.

Los endpoints históricos, retención, Streamlit, reportes e inteligencia artificial permanecen fuera de alcance y requieren definición independiente.
