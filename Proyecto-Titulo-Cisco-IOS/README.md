# Auditor de Configuraciones Cisco IOS/IOS XE

Sistema de auditoría técnica que analiza configuraciones y estado operacional de dispositivos Cisco IOS e IOS XE. Utiliza reglas deterministas para detectar errores, inconsistencias, riesgos y malas prácticas, conserva evidencia trazable y genera evaluaciones y recomendaciones sin modificar los dispositivos.

El principio central del proyecto es simple: **las reglas deterministas realizan la auditoría técnica; la inteligencia artificial futura explicará sus resultados**.

## Descripción del proyecto

El auditor recibe archivos locales `running-config` o recopila información mediante una única sesión SSH de solo lectura. La configuración se procesa con CiscoConfParse, las salidas operacionales soportadas se estructuran con TextFSM y las reglas trabajan exclusivamente sobre contextos normalizados e inmutables.

Es un Proyecto de Título de Ingeniería en Conectividad y Redes. El dominio principal es redes; la programación, la ciberseguridad y la inteligencia artificial actúan como disciplinas de apoyo para automatizar el análisis, proteger la información y facilitar la interpretación de resultados.

## Problema que aborda

La revisión manual de configuraciones de red puede ser extensa, difícil de estandarizar y propensa a omisiones. Además, una configuración aislada no siempre permite comprender el estado operacional del equipo.

El proyecto busca ofrecer resultados reproducibles y trazables al correlacionar configuración y datos operacionales mediante condiciones explícitas. Es una herramienta de apoyo: no sustituye el criterio ni la responsabilidad del profesional de redes.

## Cómo funciona

Flujo implementado actualmente:

```text
Dispositivo Cisco IOS/IOS XE
             |
             | SSH de solo lectura
             v
          Netmiko
             |
             v
     Evidencias trazables
             |
             v
          Validación
             |
       +-----+------------------+
       |                        |
       v                        v
 running-config            comandos show
 CiscoConfParse               TextFSM
       |                        |
       +-----------+------------+
                   |
                   v
          Contextos inmutables
                   |
                   v
          Reglas deterministas
                   |
             RuleEvaluation
                   |
             FAIL -> Finding
                   |
                   v
          Resultado integral
                   |
                   v
             FastAPI actual
```

Evolución prevista, separada del flujo ya implementado:

```text
Persistencia PostgreSQL (Incremento 9)
                   |
                   v
          Interfaz de usuario
                   |
                   v
 Asistente conversacional con inteligencia artificial
```

## Diagnóstico determinista

Cada regla produce una `RuleEvaluation` con uno de cinco estados:

| Estado | Significado |
|---|---|
| `PASS` | La regla pudo evaluarse y la condición técnica se cumple. |
| `FAIL` | La regla pudo evaluarse y detectó un incumplimiento o riesgo. |
| `NOT_APPLICABLE` | La regla no corresponde al dispositivo o contexto analizado. |
| `NOT_EVALUATED` | La información disponible no permite completar la evaluación. |
| `ERROR` | Ocurrió un fallo inesperado durante la evaluación. |

Todas las evaluaciones se conservan. Un `Finding` se crea exclusivamente a partir de una evaluación `FAIL`; los demás estados nunca generan hallazgos. La misma entrada y el mismo contexto deben producir resultados técnicos equivalentes.

## Inteligencia artificial

El objetivo futuro incluye un asistente conversacional para consultar una auditoría en lenguaje natural. Podrá responder preguntas como:

- ¿Por qué esta configuración fue marcada como riesgosa?
- ¿Qué significa este finding?
- ¿Qué debería revisar el administrador?
- ¿Cuáles son los hallazgos más importantes?
- ¿Puedes explicar este problema en términos más sencillos?

La IA podrá explicar, resumir y contextualizar hallazgos, así como presentar recomendaciones técnicas ya validadas. No podrá decidir estados `PASS` o `FAIL`, inventar findings, cambiar severidades, evidencia o recomendaciones, ejecutar comandos ni modificar dispositivos.

Ejemplo conceptual:

```text
Regla determinista:
IOS-NTP-001 -> FAIL

Asistente futuro:
La auditoría determinista detectó que no se comprobó un servidor NTP válido.
Esto puede dificultar la sincronización horaria y la correlación temporal de
eventos y registros.
```

`IOS-NTP-001` produce el diagnóstico; la IA únicamente explica el resultado existente. La auditoría seguirá funcionando aunque la IA no esté disponible.

## Operación de solo lectura

La lista blanca aprobada para la Evaluación 2 admite exactamente ocho comandos:

```text
show running-config
show version
show ip interface brief
show ip ssh
show interfaces
show access-lists
show ntp associations
show ip ospf neighbor
```

El recolector valida los comandos antes de abrir la conexión y utiliza `send_command()`. No expone `send_config_set()` ni `config_mode()`, no ejecuta `configure terminal`, no acepta comandos arbitrarios, no guarda configuraciones y no aplica recomendaciones automáticamente.

## Arquitectura

La solución mantiene responsabilidades separadas:

1. **Recolección:** archivos locales o SSH de solo lectura mediante Netmiko.
2. **Evidencia:** contenido original, datos normalizados, fecha UTC, `execution_id` y SHA-256.
3. **Parsing:** CiscoConfParse para `running-config` y TextFSM para siete comandos operacionales.
4. **Contextos:** `AnalysisContext`, `OperationalContext` y `MultiSourceContext` inmutables.
5. **Reglas deterministas:** lógica Python y metadatos YAML.
6. **Orquestación:** validación del lote y construcción de `FullDeviceAnalysisResult`.
7. **API:** contratos FastAPI y Pydantic para archivos y análisis integrales.
8. **Persistencia:** definida para el Incremento 9, todavía no implementada.
9. **Interfaz conversacional:** evolución futura, desacoplada del diagnóstico.

La descripción completa está en [`docs/arquitectura.md`](docs/arquitectura.md).

## Tecnologías

### Implementadas

- Python 3.11 o posterior.
- Cisco IOS e IOS XE como plataformas iniciales de análisis.
- Netmiko para recopilación SSH de solo lectura.
- `ciscoconfparse2` y `CiscoConfParse` para `running-config`.
- TextFSM mediante plantillas propias para comandos `show`.
- FastAPI y Uvicorn para la API local.
- Pydantic para contratos y validación.
- pytest para pruebas automatizadas.
- YAML para metadatos de reglas.
- Git y GitHub para control de versiones y colaboración.

### En desarrollo

El Incremento 9 define PostgreSQL, SQLAlchemy con sesiones síncronas y Alembic para persistencia relacional. Psycopg está contemplado como driver, pero su selección y distribución definitivas permanecen pendientes. Ninguna de estas capacidades está implementada todavía ni es requisito para ejecutar las funciones actuales.

### Previstas

- Streamlit para la interfaz del MVP.
- Jinja2 y salidas HTML, PDF y JSON para reportes.
- Pasarela opcional para un modelo local o una API externa de IA.
- GNS3 como posible ampliación del laboratorio si se dispone legalmente de imágenes autorizadas.

Estas tecnologías no deben interpretarse como capacidades actuales.

## Estado funcional actual

El sistema puede:

- analizar archivos locales `running-config` mediante CLI y FastAPI;
- conectarse a un dispositivo mediante una sesión SSH de solo lectura;
- ejecutar los ocho comandos canónicos y crear ocho `CommandEvidence`;
- agrupar las evidencias con un `execution_id` común y fechas UTC;
- conservar salida original y normalizada y calcular SHA-256 para integridad;
- analizar `running-config` mediante CiscoConfParse;
- parsear los siete comandos operacionales mediante TextFSM, con formatos nuevos desconocidos explícitamente no evaluables;
- construir un `AnalysisContext`, siete `OperationalContext` y un `MultiSourceContext` inmutables;
- ejecutar veintiuna evaluaciones con los registros actuales habilitados, en orden determinista, y conservar todos sus estados;
- derivar findings únicamente desde `FAIL`;
- construir un `FullDeviceAnalysisResult` inmutable;
- exponer `POST /api/v1/device-analyses` con una respuesta pública sanitizada.

## Reglas deterministas actuales

| ID | Área | Propósito |
|---|---|---|
| `IOS-ADM-001` | Administración remota | Detectar Telnet permitido en líneas VTY. |
| `IOS-SRV-001` | Servicios innecesarios | Detectar el servidor HTTP sin cifrado habilitado. |
| `IOS-AUTH-001` | Autenticación | Detectar `enable password` sin `enable secret`. |
| `IOS-ADM-002` | Administración remota | Detectar SSH versión 1 habilitada. |
| `IOS-SRV-002` | Servicios innecesarios | Detectar servicios TCP/UDP pequeños habilitados. |
| `IOS-NTP-001` | NTP | Detectar que no existe un servidor NTP configurado. |
| `IOS-LOG-001` | Syslog | Detectar que no existe un servidor Syslog configurado. |
| `IOS-AUTH-002` | Autenticación | Detectar ausencia demostrable de autenticación de consola. |
| `IOS-ACL-001` | ACL | Detectar un permiso IP global any-any explícito en ACL IPv4 extendidas. |
| `IOS-OSPF-001` | OSPF | Detectar ausencia de autenticación con contexto de interfaz suficiente. |
| `IOS-SNMP-001` | SNMP | Detectar comunidades predeterminadas o RW, sin revelar valores. |
| `IOS-DOC-001` | Nomenclatura | Detectar hostname ausente o Router/Switch genérico. |
| `IOS-AUTH-003` | Autenticación | Detectar usuario local evaluable con password en vez de secret, sin revelar valores. |
| `IOS-ADM-003` | Administración remota | Detectar timeout administrativo explícitamente deshabilitado, no su ausencia. |
| `IOS-IF-001` | Interfaces | Detectar una interfaz físicamente activa con protocolo de línea inactivo. |
| `IOS-INT-002` | Interfaces | Detectar descripción ausente en una interfaz UP/UP correlacionable. |
| `IOS-ACL-002` | ACL | Detectar ACL IPv4 concordante sin aplicación configurada reconocida. |
| `IOS-NTP-002` | NTP | Comprobar sincronización según la tabla de asociaciones soportada. |
| `IOS-AVL-001` | Disponibilidad | Alertar sobre contadores acumulados elevados, con umbral documentado. |
| `IOS-OSPF-002` | OSPF | Evaluar estados observados sin inventar expectativas de vecinos ausentes. |
| `IOS-INT-001` | Interfaces | Corroborar sin uso declarado mediante marcador explícito, no inferir abandono desde down/down. |

Las primeras catorce reglas reciben exclusivamente `AnalysisContext` de `running-config`. `IOS-IF-001` recibe el `OperationalContext` derivado de `show ip interface brief`. Los nombres, metadatos y criterios se documentan en [`docs/catalogo-reglas.md`](docs/catalogo-reglas.md). La expansión para la Evaluación 2 tiene [contratos y resultados propios](docs/registro-controles-adicionales-evaluacion-2.md), con sintaxis acotada y estados no binarios; no demuestra cobertura completa de Cisco IOS.

Las otras seis reglas reciben `MultiSourceContext`. Su [contrato operacional](docs/registro-expansion-operacional-evaluacion-2.md)
documenta umbrales y límites: IOS-AVL-001 es MEDIUM por evidencia histórica, no
diagnóstico temporal; IOS-OSPF-002 usa NOT_EVALUATED sin una expectativa segura y
no emite FAIL en este corte. La ampliación se validó primero OFFLINE. Posteriormente,
el responsable informó una validación manual real contra CSR1000v IOS XE 16.9.5
con Paramiko 4.0.0: una sesión, ocho comandos, 21 evaluaciones y tres findings.
El [registro de compatibilidad](docs/registro-controles-adicionales-evaluacion-2.md#compatibilidad-ssh-del-laboratorio-y-validación-manual-reportada)
distingue ese resultado de las pruebas sintéticas; no se repitió SSH en este ajuste.

Campaña integral sintética para capturas, desde el directorio del proyecto:

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe scripts/evaluacion_2/run_validation_scenarios.py --summary-only
```

Las fixtures operacionales son sintéticas y están etiquetadas como tales; no son
salidas recopiladas de un router. La IA continúa pendiente para la Evaluación 3.

## Seguridad y privacidad

- Las credenciales SSH son transitorias y nunca deben almacenarse en el repositorio, logs, respuestas o documentación.
- La contraseña del contrato API utiliza `SecretStr` y solo se revela internamente para crear la conexión.
- Los errores públicos están sanitizados y no incluyen credenciales ni detalles internos del dispositivo.
- El DTO integral público excluye host de conexión, `raw_output`, `normalized_output`, configuraciones completas y contextos operacionales completos.
- La configuración completa tampoco podrá enviarse a la futura IA; antes de cualquier integración deberá aplicarse sanitización.
- La lista blanca impide ejecutar comandos fuera del alcance aprobado.
- Ningún componente aplica cambios sobre los dispositivos.
- SHA-256 permite comprobar integridad; no cifra el contenido ni aporta confidencialidad.

## API

Iniciar el servicio local únicamente en loopback:

```powershell
python -m uvicorn ios_auditor.api.app:app --host 127.0.0.1 --port 8000
```

Rutas disponibles:

- `GET /health`: estado y versión del servicio.
- `GET /api/v1/rules`: catálogo habilitado de `running-config` (catorce reglas); las operacionales se evalúan en el flujo integral.
- `POST /api/v1/analyses`: análisis síncrono de un archivo.
- `GET /api/v1/analyses/{analysis_id}`: resultado de un archivo analizado.
- `GET /api/v1/analyses/{analysis_id}/evaluations`: evaluaciones del análisis.
- `GET /api/v1/analyses/{analysis_id}/findings`: hallazgos derivados de `FAIL`.
- `POST /api/v1/device-analyses`: análisis integral mediante SSH de solo lectura.

La especificación interactiva generada por FastAPI queda disponible en `http://127.0.0.1:8000/docs` y `http://127.0.0.1:8000/redoc` durante el desarrollo.

## Instalación y ejecución

Crear y activar un entorno virtual en PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Si `python` no está disponible globalmente, puede utilizarse directamente `.\.venv\Scripts\python.exe` después de crear el entorno.

`pyproject.toml` exige `paramiko>=4,<5`: Paramiko ya es una dependencia de Netmiko,
y este límite evita instalar 5.x, que eliminó los KEX SHA-1 ofrecidos por el
laboratorio CSR1000v IOS XE 16.9.5. La versión probada manualmente fue 4.0.0;
no se certifican todas las versiones 4.x. Es una compatibilidad acotada con ese
laboratorio heredado, no una recomendación de algoritmos para producción ni un
cambio del router por NetAudit. Revisar el límite cuando se actualice el laboratorio;
no constituye un bloqueo completo de versiones de todas las dependencias.

Analizar un archivo y obtener JSON compacto:

```powershell
python -m ios_auditor analyze samples/running_config_incorrecta.cfg
```

Solicitar una salida legible:

```powershell
python -m ios_auditor analyze samples/running_config_incorrecta.cfg --pretty
```

Ejemplo de carga mediante la API:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/analyses" `
  -F "file=@samples\running_config_incorrecta.cfg"
```

La carga acepta `.cfg`, `.conf` y `.txt` hasta 2 MiB, procesa el contenido en memoria y no escribe los archivos recibidos. PostgreSQL, Docker, WSL y las dependencias de persistencia no son necesarios para las capacidades implementadas.

## Corte de versiones para la auditoría académica

Las capacidades y las ocho reglas de auditoría descritas en este README corresponden a `main`. La ampliación de Evaluación 2 está en [feature/evaluacion-2-validacion](https://github.com/thomasdbs21/grupo-1/tree/feature/evaluacion-2-validacion), commit `d3d05ca`, pendiente de fusión. Esa rama contiene 14 reglas de configuración y 7 reglas operacionales, ocho evidencias y siete contextos operacionales. Su catálogo y sus registros deben consultarse en esa misma rama.

NetAudit separa la detección técnica de la explicación: el motor determinista evalúa evidencia verificable y la IA futura apoyará la interpretación de resultados. La retroalimentación docente motivó hacer más explícita esta separación y el alcance de solo lectura.

La [presentación del 6 de octubre](../Entregables-APT/Fase-2/Grupales/NetAudit_Evaluacion_2_APT_06-10-2026.pptx) corresponde a la versión ampliada. El [registro de auditoría](../Avances-del-Proyecto/Auditoria-2026-10-13.md) identifica qué se verificó en cada versión.

## Pruebas

La suite se ejecuta con:

```powershell
$env:PYTHONUTF8 = '1'
python -m pytest -q
```

Las pruebas automatizadas usan dobles, mocks y datos sintéticos para los flujos SSH; no necesitan conexión a un dispositivo real. **Al cierre del Incremento 8, la suite completa alcanzó 314 pruebas aprobadas.** Esta cifra no corresponde a una implementación del Incremento 9. La ejecución del 12/10/2026 sobre main obtuvo `314 passed, 1 warning in 7.77s`; el warning es externo (Starlette/AnyIO). La rama de Evaluación 2 obtuvo `703 passed, 1 warning in 9.67s`.

## Estado del desarrollo

| Capacidad | Estado |
|---|---|
| Análisis offline | Implementado |
| Reglas deterministas | Implementado |
| SSH de solo lectura | Implementado |
| Parsing TextFSM | Implementado |
| Análisis integral | Implementado |
| API FastAPI | Implementado |
| Persistencia PostgreSQL | Definida para el Incremento 9; no implementada |
| Interfaz de usuario final | Pendiente |
| Asistente conversacional | Pendiente |
| Explicaciones mediante IA | Pendiente |
| Reportes finales | Pendiente |

## Laboratorio de validación

Las validaciones reales controladas de los Incrementos 4 a 8 utilizaron un CSR1000v con Cisco IOS XE 16.9.5 sobre VirtualBox. Se comprobaron la conexión SSH de solo lectura, la lista blanca, la evidencia y el análisis integral sin publicar datos reales del dispositivo.

GNS3 permanece como ampliación futura opcional y no debe interpretarse como una plataforma ya utilizada.

## Estructura principal

```text
.
├── docs/                     # Arquitectura, decisiones y planificación
├── samples/                  # Configuraciones sintéticas de ejemplo
├── src/ios_auditor/
│   ├── api/                  # FastAPI, contratos y repositorio temporal
│   ├── collectors/           # Recopilación SSH de solo lectura
│   ├── domain/               # Modelos tipados e inmutables
│   ├── parsers/              # CiscoConfParse y TextFSM
│   ├── resources/            # Metadatos YAML y plantillas TextFSM
│   ├── rules/                # Lógica determinista y registros
│   └── services/             # Orquestación, análisis y serialización
└── tests/
    ├── integration/
    └── unit/
```

## Documentación

- [Arquitectura](docs/arquitectura.md)
- [Decisiones técnicas](docs/decisiones-tecnicas.md)
- [Plan incremental](docs/plan-incremental.md)
- [Catálogo de reglas](docs/catalogo-reglas.md)
- [Expansión y validación de la Evaluación 2](docs/registro-expansion-reglas-evaluacion-2.md)
- [Expansión operacional de la Evaluación 2](docs/registro-expansion-operacional-evaluacion-2.md)
- [Definición del Incremento 9](docs/definicion-incremento-9-persistencia-relacional.md)

## Alcance y limitaciones

- El alcance inicial se limita a Cisco IOS e IOS XE y a un laboratorio controlado.
- La cobertura actual es de veintiuna reglas (catorce de configuración y siete operacionales/multifuente), no del catálogo completo previsto para el MVP.
- Solo ocho comandos SSH están autorizados; siete salidas `show` tienen parsing TextFSM acotado.
- El repositorio temporal de la API de archivos conserva como máximo 100 resultados en memoria y pierde su contenido al reiniciar.
- La persistencia PostgreSQL y la integración con los endpoints actuales todavía no están implementadas.
- La interfaz final, el chatbot, los reportes y la explicación mediante IA continúan pendientes.
- El sistema no modifica dispositivos ni aplica recomendaciones automáticamente.
- La herramienta apoya al profesional de redes; la revisión y aplicación de cambios siguen bajo su responsabilidad.

## Contexto académico

**Proyecto de Título — Ingeniería en Conectividad y Redes — Duoc UC.**

La conectividad y las redes constituyen el eje del proyecto. El desarrollo de software estructura la automatización, la ciberseguridad orienta los controles y la futura IA facilitará la explicación de resultados determinados previamente por las reglas.
