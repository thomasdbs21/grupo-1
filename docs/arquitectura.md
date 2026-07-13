# Arquitectura del auditor Cisco IOS

## 1. Propósito de la arquitectura

La arquitectura define un sistema capaz de analizar configuraciones Cisco IOS mediante reglas deterministas, conservar evidencia técnica trazable y producir evaluaciones reproducibles. La inteligencia artificial será opcional y se limitará a explicar, resumir y priorizar hallazgos que el motor técnico ya haya validado.

El sistema operará en modo de solo lectura y no ejecutará cambios automáticos sobre los dispositivos.

## 2. Principios arquitectónicos

- **Operación de solo lectura:** las fuentes se consultan sin modificar dispositivos ni configuraciones.
- **Ausencia de cambios automáticos:** el sistema no entra al modo de configuración ni aplica recomendaciones.
- **Separación de responsabilidades:** entrada, recopilación, parsing, normalización, reglas, persistencia, API, interfaz, reportes e IA permanecen desacoplados.
- **Reglas deterministas:** el mismo contexto produce resultados técnicos equivalentes.
- **Evidencia trazable:** cada evaluación puede relacionarse con su origen, contenido, fecha, hash y ejecución.
- **Contexto normalizado e inmutable:** las reglas reciben una representación estructurada que no pueden modificar.
- **Inteligencia artificial opcional:** la IA no origina reglas, evaluaciones ni hallazgos.
- **Protección de credenciales:** los secretos no se almacenan en texto plano ni se exponen en salidas.
- **Desarrollo incremental:** cada etapa incorpora capacidades verificables sin anticipar componentes futuros.
- **Independencia técnica de la IA:** el análisis y las explicaciones básicas funcionan aunque la pasarela de IA no esté disponible.

## 3. Diagrama lógico general

```text
Fuentes
  Archivo running-config                          [PRIMER INCREMENTO]
  Dispositivo Cisco IOS                           [MVP / FUTURO]
            |
            v
Entrada de archivo                                [PRIMER INCREMENTO]
o recopilación SSH                                [MVP]
            |
            v
Conservación de evidencia original                [PRIMER INCREMENTO]
            |
            v
Parsing: ciscoconfparse2 (clase CiscoConfParse)   [PRIMER INCREMENTO]
         TextFSM para comandos show               [MVP]
            |
            v
Normalización                                     [PRIMER INCREMENTO]
            |
            v
Contexto inmutable                                [PRIMER INCREMENTO]
            |
            v
Carga YAML segura y RuleRegistry                  [INCREMENTO 2]
            |
            v
Motor de reglas deterministas                     [PRIMER INCREMENTO]
            |
            v
RuleEvaluation                                    [PRIMER INCREMENTO]
            |
            +---- estado distinto de FAIL ------> sin Finding
            |
            +---- estado FAIL -------------------> Finding
                                                       |
                                                       v
Repositorio temporal en memoria (máximo 100)      [INCREMENTO 3]
            |
            v
API FastAPI local y síncrona                      [INCREMENTO 3]
            |
            v
Interfaz Streamlit y reportes                     [MVP]
            |
            v
Pasarela opcional de inteligencia artificial      [MVP / FUTURO]

Mejoras posteriores: pyATS/Genie, colas de trabajos,
alta disponibilidad y soporte para más plataformas. [FUTURO]
```

## 4. Componentes de la arquitectura

### 4.1 Entrada de archivos

- **Responsabilidad:** recibir y validar la ruta de un archivo local `running-config`.
- **Entrada:** ruta proporcionada por el usuario.
- **Salida:** contenido legible o error de entrada estructurado.
- **Relación:** entrega el contenido al gestor de evidencia y al parser.
- **Etapa:** primer incremento.

### 4.2 Recopilación SSH futura

- **Responsabilidad:** recopilar información autorizada desde dispositivos Cisco IOS en modo de solo lectura.
- **Entrada:** dispositivo, credenciales seguras y comandos de una lista blanca.
- **Salida:** salidas originales o errores de conexión estructurados.
- **Relación:** usa Netmiko y entrega resultados al gestor de evidencia.
- **Etapa:** MVP, posterior al primer incremento.

### 4.3 Gestión de evidencia

- **Responsabilidad:** conservar origen, fecha, contenido original y normalizado, fragmento relevante, hash e identificador de ejecución.
- **Entrada:** archivos o salidas recopiladas.
- **Salida:** objetos `Evidence` trazables.
- **Relación:** abastece parsers, contexto, evaluaciones, hallazgos y persistencia.
- **Etapa:** conceptual y local en el primer incremento; persistente en el MVP.

### 4.4 Parser de running-config con ciscoconfparse2

- **Responsabilidad:** interpretar la estructura jerárquica de `running-config` mediante `ciscoconfparse2`; la clase utilizada continúa llamándose `CiscoConfParse`.
- **Entrada:** contenido original validado.
- **Salida:** representación parseada o error explícito.
- **Relación:** entrega datos al normalizador sin alterar la evidencia original.
- **Etapa:** primer incremento.

### 4.5 Parser futuro de comandos show con TextFSM

- **Responsabilidad:** transformar salidas de comandos `show` en registros estructurados.
- **Entrada:** salida original y plantilla TextFSM correspondiente.
- **Salida:** datos operacionales parseados o error explícito.
- **Relación:** recibe evidencia desde SSH y alimenta al normalizador.
- **Etapa:** MVP, incremento posterior.

### 4.6 Normalizador

- **Responsabilidad:** unificar datos parseados en estructuras estables para las reglas.
- **Entrada:** resultados de `ciscoconfparse2` (`CiscoConfParse`) o TextFSM y metadatos disponibles.
- **Salida:** datos normalizados.
- **Relación:** construye el contexto sin reemplazar el contenido original.
- **Etapa:** primer incremento y ampliaciones posteriores.

### 4.7 Contexto de análisis inmutable

- **Responsabilidad:** representar de forma estructurada las fuentes disponibles para una ejecución.
- **Entrada:** datos normalizados, metadatos, evidencias y errores de fuentes.
- **Salida:** contexto inmutable para el motor de reglas.
- **Relación:** única entrada técnica permitida para las reglas.
- **Etapa:** primer incremento.

### 4.8 Registro de reglas

- **Responsabilidad:** identificar, versionar, habilitar y cargar reglas junto con sus metadatos declarativos.
- **Entrada:** clases Python y exactamente los archivos YAML esperados, leídos mediante carga segura.
- **Salida:** conjunto validado de reglas en un orden oficial determinista; el subconjunto habilitado alimenta al motor.
- **Relación:** asocia cada clase con un `RuleMetadata` inmutable, rechaza duplicados e inconsistencias y entrega reglas al motor sin concederles acceso a infraestructura.
- **Etapa:** completado en el Incremento 2.

El YAML no contiene condiciones ni lógica de evaluación. La detección permanece exclusivamente en Python. El registro no descubre archivos arbitrarios: solo carga nombres previamente autorizados dentro de la carpeta de recursos.

### 4.9 Motor de reglas

- **Responsabilidad:** ejecutar reglas deterministas sobre el contexto.
- **Entrada:** contexto inmutable y reglas registradas.
- **Salida:** resultados estructurados de evaluación.
- **Relación:** entrega todos los resultados al gestor de evaluaciones.
- **Etapa:** primer incremento.

### 4.10 Gestor de evaluaciones

- **Responsabilidad:** registrar cada resultado como `PASS`, `FAIL`, `NOT_APPLICABLE`, `NOT_EVALUATED` o `ERROR`.
- **Entrada:** resultados del motor de reglas.
- **Salida:** objetos `RuleEvaluation`.
- **Relación:** alimenta el gestor de hallazgos y, posteriormente, la persistencia.
- **Etapa:** primer incremento a nivel conceptual; persistencia en el MVP.

### 4.11 Gestor de hallazgos

- **Responsabilidad:** crear un `Finding` únicamente desde una evaluación `FAIL`.
- **Entrada:** evaluaciones y evidencias relacionadas.
- **Salida:** hallazgos técnicos trazables.
- **Relación:** consume `RuleEvaluation` y entrega resultados a salida, persistencia, API y reportes.
- **Etapa:** primer incremento.

### 4.12 Repositorio temporal y persistencia futura

- **Responsabilidad:** conservar temporalmente hasta 100 resultados asociados a UUID y eliminar el más antiguo al superar el límite.
- **Entrada:** resultados sanitizados ya producidos por el analizador.
- **Salida:** consultas por identificador durante la vida del proceso.
- **Relación:** sirve a FastAPI sin ser accedido por las reglas; utiliza bloqueo para concurrencia básica y no escribe archivos.
- **Etapa:** repositorio en memoria completado en el Incremento 3. PostgreSQL, SQLAlchemy y Alembic lo reemplazarán en el Incremento 6.

### 4.13 FastAPI local

- **Responsabilidad:** exponer salud, reglas habilitadas, carga, análisis síncrono y consulta de resultados.
- **Entrada:** solicitudes validadas y archivos multipart `.cfg`, `.conf` o `.txt` de hasta 2 MiB.
- **Salida:** respuestas tipadas sin rutas absolutas ni configuración completa y documentación OpenAPI.
- **Relación:** usa los servicios existentes, el registro central y el repositorio temporal; no contiene lógica de reglas.
- **Etapa:** completado en el Incremento 3.

Los archivos se procesan en memoria como UTF-8 o UTF-8 con BOM. El nombre se reduce a su componente base, se rechazan binarios y no se escriben cargas en disco.

### 4.14 Streamlit futuro

- **Responsabilidad:** proporcionar la interfaz inicial para carga, selección y visualización.
- **Entrada:** datos de la API o servicios definidos para el MVP.
- **Salida:** vistas de evaluaciones, hallazgos, evidencias e historial.
- **Relación:** presenta resultados sin modificar su estado técnico.
- **Etapa:** MVP, incremento futuro.

### 4.15 Generación de reportes futura

- **Responsabilidad:** generar salidas JSON, HTML y PDF sanitizadas y trazables.
- **Entrada:** ejecuciones, evaluaciones, hallazgos y evidencias autorizadas.
- **Salida:** reportes por severidad y detalle técnico.
- **Relación:** consume datos validados; no vuelve a evaluar configuraciones.
- **Etapa:** JSON básico en el primer incremento; HTML y PDF en el MVP.

### 4.16 Pasarela opcional de inteligencia artificial

- **Responsabilidad:** explicar, resumir y priorizar hallazgos validados.
- **Entrada:** información estructurada y sanitizada.
- **Salida:** explicaciones complementarias sin autoridad sobre el resultado técnico.
- **Relación:** consume hallazgos existentes y permanece aislada del motor de reglas.
- **Etapa:** MVP tardío o mejora futura.

## 5. Flujo del primer incremento

1. El usuario entrega la ruta de un archivo `running-config`.
2. Se valida que el archivo exista y sea legible.
3. Se conserva el contenido original.
4. Se calcula un hash.
5. `ciscoconfparse2`, mediante la clase `CiscoConfParse`, procesa la configuración.
6. Se crea un contexto normalizado e inmutable.
7. Se ejecutan tres reglas piloto.
8. Se almacenan conceptualmente todas las evaluaciones.
9. Se crean `findings` únicamente desde resultados `FAIL`.
10. Se entrega una salida JSON.

## 6. Flujo futuro mediante GNS3 y SSH

Sin implementar todavía, el flujo previsto será:

1. Selección de un dispositivo del laboratorio.
2. Obtención segura de credenciales.
3. Conexión mediante Netmiko.
4. Ejecución de comandos `show` autorizados mediante una lista blanca.
5. Conservación de la salida original.
6. Parsing con `ciscoconfparse2` (`CiscoConfParse`) o TextFSM, según la fuente.
7. Normalización de los resultados.
8. Creación del contexto inmutable.
9. Ejecución de reglas deterministas.
10. Persistencia de ejecuciones, evidencias, evaluaciones y hallazgos.
11. Presentación de resultados en la interfaz.
12. Explicación opcional mediante inteligencia artificial sobre datos sanitizados.

## 7. Aislamiento del motor de reglas

Las reglas:

- No acceden a SSH.
- No acceden a Netmiko.
- No ejecutan comandos.
- No consultan directamente la base de datos.
- No llaman a la inteligencia artificial.
- No modifican el contexto.
- No escriben archivos arbitrarios.
- Solo reciben un contexto normalizado e inmutable.
- Solo devuelven resultados estructurados y deterministas.

## 8. Modelo conceptual

- **AnalysisRun:** representa una ejecución completa, su fecha, estado, origen y relaciones con evidencias y resultados.
- **Device:** identifica el equipo o fuente lógica analizada, incluyendo plataforma y metadatos no sensibles.
- **Evidence:** conserva la fuente, fecha, contenido original, contenido normalizado, fragmento relevante, hash e identificadores relacionados.
- **RuleDefinition:** describe identidad, versión, metadatos y referencia a la lógica determinista de una regla.
- **RuleEvaluation:** registra el resultado de toda regla ejecutada. Sus estados posibles son `PASS`, `FAIL`, `NOT_APPLICABLE`, `NOT_EVALUATED` y `ERROR`.
- **Finding:** representa un incumplimiento técnico y se crea únicamente desde una `RuleEvaluation` cuyo estado sea `FAIL`.

Los estados diferentes de `FAIL` permanecen registrados como evaluaciones, pero nunca generan un `Finding`.

## 9. Manejo de errores

- **Ruta inexistente:** error de entrada antes de leer o analizar.
- **Archivo no legible:** error de acceso con mensaje seguro y claro.
- **Archivo vacío:** entrada inválida; no se simula una evaluación.
- **Configuración no reconocible:** se informa que el contenido no cumple el formato mínimo esperado.
- **Error de parsing:** se conserva la evidencia original y se registra el fallo explícitamente.
- **Fuente requerida ausente:** la regla aplicable produce `NOT_EVALUATED`.
- **Error interno de una regla:** la evaluación produce `ERROR` y conserva trazabilidad.
- **Error futuro de conexión:** se registra como error de recopilación sin ejecutar reglas que dependan de la fuente ausente.
- **IA no disponible:** se entrega la explicación técnica básica y el análisis continúa funcionando.

Un error interno nunca debe convertirse silenciosamente en `PASS` ni en `FAIL`. La caída de la IA no debe impedir el análisis técnico.

## 10. Seguridad

- Las credenciales permanecerán fuera del repositorio.
- Los archivos `.env` estarán excluidos por `.gitignore`; solo podrá versionarse un `.env.example` sin secretos.
- En incrementos futuros se utilizarán variables de entorno o un gestor de secretos.
- La información se sanitizará antes de enviarse a la inteligencia artificial.
- Los secretos se eliminarán o enmascararán en entradas y salidas.
- Netmiko solo ejecutará comandos incluidos en una lista blanca.
- Se prohíben comandos de configuración, guardado, eliminación, reinicio o depuración destructiva.
- Los logs y reportes no incluirán credenciales ni secretos.
- Las conexiones usarán un usuario SSH con privilegios mínimos suficientes para consultas autorizadas.

## 11. Arquitectura por etapas

### Primer incremento

- Archivo `running-config` local.
- `ciscoconfparse2` (clase `CiscoConfParse`).
- Contexto normalizado e inmutable.
- Tres reglas piloto.
- Salida JSON.
- Pruebas con pytest.

### Incremento 2

- Tres archivos YAML oficiales y versionados.
- Modelo `RuleMetadata` inmutable.
- Carga segura mediante `yaml.safe_load`.
- Validación de campos, versiones, severidades, IDs y duplicados.
- `RuleRegistry` central con orden determinista.
- Ejecución exclusiva de reglas habilitadas.
- Lógica técnica conservada en Python.

### Incremento 3

- FastAPI y Uvicorn para servicio local en `127.0.0.1`.
- Análisis síncrono de cargas multipart en memoria.
- Límite de 2 MiB y extensiones controladas.
- Modelos API tipados mediante Pydantic.
- Repositorio temporal concurrente de hasta 100 análisis.
- Consulta de resultados, evaluaciones y hallazgos mediante UUID.
- Errores estructurados y logging sin contenido sensible.

### MVP

- Catálogo de 20 a 25 reglas.
- FastAPI.
- Netmiko.
- TextFSM.
- PostgreSQL, SQLAlchemy y Alembic.
- Streamlit.
- Reportes JSON, HTML y PDF.
- Pasarela de IA opcional.
- Validación en laboratorio GNS3 con IOSv e IOSvL2.

### Mejoras futuras

- pyATS/Genie.
- Cola de trabajos.
- Redis o Celery.
- Alta disponibilidad.
- Más plataformas.
- Más protocolos.
- Gestión avanzada de secretos.
- Interfaz frontend independiente.

## 12. Decisiones pendientes

- Método definitivo de almacenamiento de credenciales.
- Uso de un modelo local o una API externa de inteligencia artificial.
- Plantillas TextFSM definitivas.
- Formato final de los reportes.
- Diseño final de Streamlit.
- Necesidad y tecnología de procesamiento en segundo plano.
- Política de retención de evidencias.
- Selección definitiva de las reglas que entrarán al MVP.
