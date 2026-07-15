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
  Dispositivo Cisco IOS/IOS XE                    [INCREMENTO 4]
            |
            v
Entrada de archivo                                [PRIMER INCREMENTO]
o recopilación SSH de solo lectura                [INCREMENTO 4]
            |
            v
CommandEvidence y evidencia original              [INCREMENTO 4]
            |
            v
Orquestador de running-config recopilado           [INCREMENTO 4]
            |
            v
Parsing: ciscoconfparse2 (clase CiscoConfParse)   [PRIMER INCREMENTO]
         TextFSM para comandos show               [INCREMENTO 5]
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
Repositorio temporal en memoria (máximo 100)      [INCREMENTO 3; ARCHIVOS]
            |
            v
API FastAPI local y síncrona                      [INCREMENTO 3; SIN SSH]
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

### 4.2 Recopilación SSH de solo lectura

- **Responsabilidad:** recopilar información autorizada desde dispositivos Cisco IOS e IOS XE sin modificar su configuración.
- **Entrada:** host, puerto, credenciales entregadas en tiempo de ejecución y uno o varios comandos de la lista blanca inmutable.
- **Salida:** objetos `CommandEvidence` inmutables o errores seguros de recopilación.
- **Relación:** `NetmikoCollector` valida todos los comandos antes de conectar, reutiliza una sesión y la cierra mediante `disconnect()`.
- **Etapa:** completado en el Incremento 4.

La lista blanca actual contiene `show running-config`, `show version`, `show ip interface brief` y `show ip ssh`. La autorización es exacta: pipes, argumentos adicionales, punto y coma y saltos de línea se rechazan. El recolector no utiliza métodos de configuración.

### 4.2.1 Orquestador de análisis recopilado

- **Responsabilidad:** coordinar una evidencia de `show running-config` con el analizador existente.
- **Entrada:** un objeto compatible con el protocolo `RunningConfigCollector`, un UUID opcional y un `RuleRegistry` opcional.
- **Salida:** `CollectedAnalysisResult`, que conserva la `CommandEvidence` y el `AnalysisResult`.
- **Relación:** `analyze_collected_running_config()` valida comando, UUID y SHA-256, y entrega `raw_output.encode("utf-8")` a `analyze_bytes()`.
- **Etapa:** completado en el Incremento 4.

El orquestador no almacena el recolector ni credenciales. Tampoco contiene parsing o lógica de reglas: reutiliza el flujo determinista en memoria.

### 4.3 Gestión de evidencia

- **Responsabilidad:** conservar origen, fecha, contenido original y normalizado, fragmento relevante, hash e identificador de ejecución.
- **Entrada:** archivos o salidas recopiladas.
- **Salida:** `CommandEvidence` para recopilación y objetos `Evidence` para fragmentos utilizados por las reglas.
- **Relación:** abastece parsers, contexto, evaluaciones, hallazgos y persistencia.
- **Etapa:** evidencia local de archivos desde el primer incremento y `CommandEvidence` desde el Incremento 4; persistencia futura.

### 4.4 Parser de running-config con ciscoconfparse2

- **Responsabilidad:** interpretar la estructura jerárquica de `running-config` mediante `ciscoconfparse2`; la clase utilizada continúa llamándose `CiscoConfParse`.
- **Entrada:** contenido original validado.
- **Salida:** representación parseada o error explícito.
- **Relación:** entrega datos al normalizador sin alterar la evidencia original.
- **Etapa:** primer incremento.

### 4.5 Parser de comandos show con TextFSM

- **Responsabilidad:** transformar salidas de comandos `show` en registros estructurados.
- **Entrada:** comando normalizado, salida normalizada y plantilla TextFSM propia correspondiente.
- **Salida:** `ShowVersionData`, `ShowIpInterfaceBriefData` o `ShowIpSshData`, o un error seguro y explícito.
- **Relación:** `parse_show_command()` utiliza un mapeo inmutable, carga recursos empaquetados y no accede a SSH.
- **Etapa:** completado en el Incremento 5.

TextFSM procesa exclusivamente `show version`, `show ip interface brief` y `show ip ssh`. `show running-config` continúa siendo responsabilidad de `ciscoconfparse2` y `CiscoConfParse`.

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

Existen dos contextos separados:

- `AnalysisContext`, dedicado a datos normalizados de `running-config`;
- `OperationalContext`, dedicado a un comando `show`, su modelo tipado y la trazabilidad mediante UUID, comando, fecha UTC y SHA-256.

`OperationalContext` no contiene `raw_output`, `normalized_output`, credenciales ni objetos Netmiko. Ambos contextos son inmutables y las reglas reciben solamente el que corresponde a su fuente.

### 4.7.1 Servicio operational_analysis

- **Responsabilidad:** validar una `CommandEvidence` y construir el contexto operacional.
- **Entrada:** una evidencia ya recopilada; no recibe credenciales ni conexiones.
- **Salida:** `OperationalContext` o una excepción segura.
- **Relación:** `parse_collected_show_evidence()` verifica comando, SHA-256, normalización y fecha UTC antes de llamar a `parse_show_command()`.
- **Etapa:** completado en el Incremento 5.

### 4.8 Registro de reglas

- **Responsabilidad:** identificar, versionar, habilitar y cargar reglas junto con sus metadatos declarativos.
- **Entrada:** clases Python y exactamente los archivos YAML esperados, leídos mediante carga segura.
- **Salida:** conjunto validado de reglas en un orden oficial determinista; el subconjunto habilitado alimenta al motor.
- **Relación:** asocia cada clase con un `RuleMetadata` inmutable, rechaza duplicados e inconsistencias y entrega reglas al motor sin concederles acceso a infraestructura.
- **Etapa:** completado en el Incremento 2.

El YAML no contiene condiciones ni lógica de evaluación. La detección permanece exclusivamente en Python. El registro no descubre archivos arbitrarios: solo carga nombres previamente autorizados dentro de la carpeta de recursos.

El `RuleRegistry` existente continúa reservado a las tres reglas de `running-config`. `IOS-IF-001` se carga mediante `get_interface_operational_rule()` y permanece separada para no mezclar contratos de contexto ni alterar las evaluaciones offline.

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
- **Etapa:** repositorio en memoria completado en el Incremento 3. La persistencia mediante PostgreSQL, SQLAlchemy y Alembic permanece como alternativa futura pendiente de planificación.

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

## 6. Flujo implementado mediante laboratorio virtual y SSH

La validación real de este flujo se efectuó con un CSR1000v IOS XE 16.9.5 ejecutado en VirtualBox. GNS3 no se utilizó y queda solamente como ampliación futura opcional si se dispone legalmente de imágenes IOSv o IOSvL2 autorizadas.

El flujo completado para `running-config` es:

1. Las credenciales se entregan al recolector en tiempo de ejecución y permanecen fuera de resultados y representaciones.
2. `NetmikoCollector` recibe exclusivamente comandos incluidos en la lista blanca.
3. La validación exacta ocurre antes de abrir la conexión.
4. Netmiko utiliza `device_type="cisco_ios"` para los dispositivos Cisco IOS e IOS XE considerados.
5. Cada comando genera una `CommandEvidence` con UUID, fecha UTC, salida original, salida normalizada y hash.
6. La sesión se cierra antes de devolver las evidencias.
7. Para el flujo integrado, `analyze_collected_running_config()` solicita únicamente `show running-config`.
8. El orquestador verifica la integridad y entrega la salida original codificada como UTF-8 a `analyze_bytes()`.
9. `parse_running_config()` procesa y normaliza el contenido mediante `ciscoconfparse2` y `CiscoConfParse`.
10. Se crea un `AnalysisContext` inmutable.
11. `RuleRegistry` entrega las reglas habilitadas en orden determinista.
12. Todas las reglas producen evaluaciones y solo los estados `FAIL` producen findings.

El flujo operacional completado en el Incremento 5 es:

```text
NetmikoCollector
        |
        v
CommandEvidence
        |
        v
parse_collected_show_evidence()
        |
        v
parse_show_command()
        |
        v
plantilla TextFSM propia
        |
        v
modelo tipado
        |
        v
OperationalContext inmutable
        |
        v
IOS-IF-001
        |
        v
RuleEvaluation
```

La validación operacional real se realizó con el CSR1000v IOS XE 16.9.5 ejecutado en VirtualBox. La persistencia, la exposición operacional mediante FastAPI, la interfaz y la inteligencia artificial continúan fuera de alcance. Las reglas no reciben el recolector en ninguna etapa.

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
- **Error de conexión:** las excepciones de autenticación, timeout y conexión se traducen a errores seguros; si no existe evidencia válida, el análisis integrado no se ejecuta.
- **IA no disponible:** se entrega la explicación técnica básica y el análisis continúa funcionando.

Un error interno nunca debe convertirse silenciosamente en `PASS` ni en `FAIL`. La caída de la IA no debe impedir el análisis técnico.

## 10. Seguridad

- Las credenciales permanecerán fuera del repositorio.
- Los archivos `.env` estarán excluidos por `.gitignore`; solo podrá versionarse un `.env.example` sin secretos.
- Las credenciales SSH se suministran en tiempo de ejecución; el mecanismo definitivo de almacenamiento seguro sigue pendiente.
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

### Incremento 4

- Netmiko para SSH de solo lectura en Cisco IOS e IOS XE.
- Lista blanca inmutable de cuatro comandos.
- Evidencia inmutable con UUID, fecha UTC, contenido original y normalizado, y SHA-256.
- Protocolo `RunningConfigCollector` para desacoplar infraestructura y aplicación.
- Orquestador `analyze_collected_running_config()` para `show running-config`.
- Identidad de hash entre `CommandEvidence` y `AnalysisResult`.
- Pruebas automatizadas sin conexión real y validaciones manuales controladas.

### Incremento 5

- TextFSM como dependencia directa y parser oficial de tres comandos `show`.
- Plantillas propias, versionadas y empaquetadas.
- Modelos tipados y `OperationalContext` inmutable.
- Servicio `operational_analysis` para integridad y parsing sin red.
- Regla operacional `IOS-IF-001`, separada del `RuleRegistry` de `running-config`.
- 28 pruebas nuevas y 124 pruebas totales aprobadas.
- Validación real sanitizada con CSR1000v IOS XE 16.9.5 en VirtualBox.

### MVP

- Catálogo de 20 a 25 reglas.
- FastAPI.
- Netmiko.
- TextFSM.
- PostgreSQL, SQLAlchemy y Alembic.
- Streamlit.
- Reportes JSON, HTML y PDF.
- Pasarela de IA opcional.
- Validación ampliada en laboratorios virtuales autorizados. GNS3 queda como opción futura si se dispone legalmente de imágenes IOSv o IOSvL2.

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
- Ampliación y versionado de plantillas TextFSM para nuevas variantes y comandos.
- Formato final de los reportes.
- Diseño final de Streamlit.
- Necesidad y tecnología de procesamiento en segundo plano.
- Política de retención de evidencias.
- Selección definitiva de las reglas que entrarán al MVP.
