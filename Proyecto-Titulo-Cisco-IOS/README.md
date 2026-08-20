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

La lista blanca admite exactamente estos cuatro comandos:

```text
show running-config
show version
show ip interface brief
show ip ssh
```

El recolector valida los comandos antes de abrir la conexión y utiliza `send_command()`. No expone `send_config_set()` ni `config_mode()`, no ejecuta `configure terminal`, no acepta comandos arbitrarios, no guarda configuraciones y no aplica recomendaciones automáticamente.

## Arquitectura

La solución mantiene responsabilidades separadas:

1. **Recolección:** archivos locales o SSH de solo lectura mediante Netmiko.
2. **Evidencia:** contenido original, datos normalizados, fecha UTC, `execution_id` y SHA-256.
3. **Parsing:** CiscoConfParse para `running-config` y TextFSM para los tres comandos operacionales soportados.
4. **Contextos:** `AnalysisContext` y `OperationalContext` inmutables.
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
- ejecutar los cuatro comandos canónicos y crear cuatro `CommandEvidence`;
- agrupar las evidencias con un `execution_id` común y fechas UTC;
- conservar salida original y normalizada y calcular SHA-256 para integridad;
- analizar `running-config` mediante CiscoConfParse;
- parsear `show version`, `show ip interface brief` y `show ip ssh` mediante TextFSM;
- construir un `AnalysisContext` y tres `OperationalContext` inmutables;
- ejecutar ocho evaluaciones en orden determinista y conservar todos sus estados;
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
| `IOS-IF-001` | Interfaces | Detectar una interfaz físicamente activa con protocolo de línea inactivo. |

Las primeras siete reglas reciben exclusivamente `AnalysisContext` de `running-config`. `IOS-IF-001` recibe el `OperationalContext` derivado de `show ip interface brief`. Los nombres, metadatos y criterios se documentan en [`docs/catalogo-reglas.md`](docs/catalogo-reglas.md).

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
- `GET /api/v1/rules`: catálogo habilitado.
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

## Pruebas

La suite se ejecuta con:

```powershell
python -m pytest
```

Las pruebas automatizadas usan dobles, mocks y datos sintéticos para los flujos SSH; no necesitan conexión a un dispositivo real. **Al cierre del Incremento 8, la suite completa alcanzó 314 pruebas aprobadas.** Esta cifra no corresponde a una implementación del Incremento 9.

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
- [Definición del Incremento 9](docs/definicion-incremento-9-persistencia-relacional.md)

## Alcance y limitaciones

- El alcance inicial se limita a Cisco IOS e IOS XE y a un laboratorio controlado.
- La cobertura actual es de ocho reglas y todavía no representa el catálogo completo previsto para el MVP.
- Solo cuatro comandos SSH están autorizados y tres salidas `show` tienen parsing TextFSM.
- El repositorio temporal de la API de archivos conserva como máximo 100 resultados en memoria y pierde su contenido al reiniciar.
- La persistencia PostgreSQL y la integración con los endpoints actuales todavía no están implementadas.
- La interfaz final, el chatbot, los reportes y la explicación mediante IA continúan pendientes.
- El sistema no modifica dispositivos ni aplica recomendaciones automáticamente.
- La herramienta apoya al profesional de redes; la revisión y aplicación de cambios siguen bajo su responsabilidad.

## Contexto académico

**Proyecto de Título — Ingeniería en Conectividad y Redes — Duoc UC.**

La conectividad y las redes constituyen el eje del proyecto. El desarrollo de software estructura la automatización, la ciberseguridad orienta los controles y la futura IA facilitará la explicación de resultados determinados previamente por las reglas.
