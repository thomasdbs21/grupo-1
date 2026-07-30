# Auditor offline de configuraciones Cisco IOS

## Propósito

Aplicación local y de solo lectura que analiza archivos `running-config` de Cisco IOS. Construye un contexto normalizado e inmutable, ejecuta tres reglas deterministas y entrega evaluaciones y hallazgos en JSON. No realiza cambios en dispositivos y no utiliza inteligencia artificial.

## Requisitos

- Python 3.11 o posterior.
- Windows 11 y PowerShell para el entorno principal del primer incremento.
- Un archivo local de configuración Cisco IOS codificado en UTF-8.

El parser utiliza la dependencia `ciscoconfparse2`; su clase principal continúa llamándose `CiscoConfParse`.

## Creación y activación de `.venv`

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Instalación

Con el entorno virtual activo:

```powershell
python -m pip install -e ".[dev]"
```

## Ejecución de la CLI

Salida JSON compacta:

```powershell
python -m ios_auditor analyze samples/running_config_incorrecta.cfg
```

Salida JSON legible:

```powershell
python -m ios_auditor analyze samples/running_config_incorrecta.cfg --pretty
```

Los errores se escriben en `stderr` y producen un código de salida distinto de cero.

La CLI continúa disponible y utiliza el mismo analizador que la API.

## API local con FastAPI

El Incremento 3 expone el analizador mediante una API REST local y síncrona. Para iniciarla:

```powershell
python -m uvicorn ios_auditor.api.app:app --host 127.0.0.1 --port 8000
```

Se utiliza `127.0.0.1` para no publicar accidentalmente el servicio en toda la red. Durante el desarrollo local, FastAPI ofrece documentación interactiva en:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

Endpoints disponibles:

- `GET /health`: estado y versión del servicio.
- `GET /api/v1/rules`: reglas habilitadas.
- `POST /api/v1/analyses`: carga y análisis síncrono de un archivo.
- `GET /api/v1/analyses/{analysis_id}`: resultado completo.
- `GET /api/v1/analyses/{analysis_id}/evaluations`: evaluaciones.
- `GET /api/v1/analyses/{analysis_id}/findings`: hallazgos.

Ejemplo de carga desde PowerShell:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/analyses" `
  -F "file=@samples\running_config_incorrecta.cfg"
```

La API acepta `.cfg`, `.conf` y `.txt`, con un máximo de 2 MiB. Procesa UTF-8 y UTF-8 con BOM directamente en memoria: no confía en rutas del cliente, no escribe archivos subidos y no devuelve rutas absolutas ni la configuración completa.

Los resultados de archivos se guardan temporalmente en memoria, con un máximo de 100 análisis. Al superar el límite se elimina el más antiguo y los datos desaparecen al reiniciar el proceso. Este repositorio no dispone todavía de persistencia durable.

## Ejecución de pruebas

```powershell
python -m pytest
```

## Estructura básica

```text
src/ios_auditor/
├── api/        # FastAPI, esquemas y repositorio temporal
├── cli.py
├── domain/     # modelos tipados e inmutables
├── parsers/    # parsing y normalización de running-config
├── resources/  # metadatos YAML declarativos de las reglas
├── rules/      # lógica determinista, carga segura y registro central
└── services/   # carga, análisis y serialización
```

Las configuraciones de ejemplo están en `samples/` y las pruebas en `tests/`.

## Reglas piloto

- `IOS-ADM-001`: detecta Telnet permitido en líneas VTY.
- `IOS-SRV-001`: detecta el servidor HTTP sin cifrado `ip http server`.
- `IOS-AUTH-001`: detecta `enable password` cuando no existe `enable secret`.

Solo las evaluaciones `FAIL` generan hallazgos. Las evidencias sensibles se redactan antes de incluirse en JSON.

## Registro y metadatos de reglas

Cada regla piloto tiene un archivo YAML versionado dentro de `src/ios_auditor/resources/rules/`. Los YAML contienen únicamente metadatos declarativos, como identidad, severidad, fuentes, plataformas, riesgo, recomendación, referencias y estado de habilitación. La lógica de evaluación permanece exclusivamente en Python.

Los archivos se cargan con `yaml.safe_load`, se validan contra campos obligatorios y se asocian con su clase Python mediante un `RuleRegistry` central. El registro rechaza IDs duplicados o inconsistentes, mantiene un orden determinista y ejecuta solamente reglas cuyo campo `enabled` sea `true`. No existe todavía una opción de CLI para alterar estos archivos.

## Limitaciones actuales

- Solo analiza archivos locales `running-config` en UTF-8.
- Implementa exactamente tres reglas piloto.
- Los metadatos solo pueden modificarse editando los YAML antes de iniciar una ejecución.
- La API conserva como máximo 100 resultados en memoria y no ofrece persistencia durable.
- No analiza estado operacional ni comandos `show`.
- La detección depende de la sintaxis soportada por Cisco IOS y `ciscoconfparse2`.

## Componentes futuros fuera de alcance

PostgreSQL, SQLAlchemy, Alembic, Streamlit, reportes HTML/PDF e inteligencia artificial no están implementados.
