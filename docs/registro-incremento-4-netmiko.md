# Registro técnico del Incremento 4: Netmiko de solo lectura

## 1. Objetivo del incremento

El Incremento 4 incorpora la recopilación SSH de solo lectura desde dispositivos Cisco IOS e IOS XE y la integra con el analizador determinista existente. Su propósito es obtener evidencia técnica desde un equipo de red sin modificarlo y reutilizar el mismo parsing, contexto inmutable, registro y reglas que ya procesaban archivos locales `running-config`.

El foco continúa siendo la conectividad y las redes. Python y los controles de seguridad complementan ese objetivo mediante automatización verificable, separación de responsabilidades y protección de credenciales.

## 2. Problema técnico resuelto

Antes de este incremento, el análisis comenzaba únicamente desde bytes o archivos locales. El proyecto no disponía de un límite formal entre una sesión SSH y el motor determinista. El incremento resuelve ese problema con dos componentes:

- `NetmikoCollector`, que ejecuta solamente comandos de consulta autorizados y produce evidencias inmutables.
- `analyze_collected_running_config()`, que valida la evidencia de `show running-config` y la entrega al analizador en memoria.

Esta solución evita archivos temporales, no duplica el parser y mantiene las reglas aisladas de Netmiko, las conexiones y las credenciales.

## 3. Alcance y exclusiones

El alcance implementado comprende:

- conexión mediante Netmiko con `device_type="cisco_ios"`, válido para los escenarios considerados de Cisco IOS e IOS XE;
- lista blanca inmutable de cuatro comandos de consulta;
- recopilación de uno o varios comandos autorizados en una sola sesión;
- evidencia original y normalizada con fecha UTC, UUID y SHA-256;
- integración de `show running-config` con el analizador determinista;
- validación del contrato entre recopilación y análisis;
- pruebas automatizadas sin conexiones reales;
- validaciones manuales controladas contra un CSR1000v.

Quedan fuera del alcance:

- comandos de configuración o cambios sobre dispositivos;
- parsing estructurado de los otros comandos `show` mediante TextFSM;
- exposición del flujo SSH mediante FastAPI;
- persistencia en PostgreSQL;
- integración con la CLI del producto, reportes o inteligencia artificial;
- almacenamiento permanente de dispositivos, ejecuciones o evidencias.

## 4. Flujo técnico completo

```text
Cisco IOS/IOS XE
        |
        v
SSH de solo lectura
        |
        v
NetmikoCollector
        |
        v
CommandEvidence de show running-config
        |
        v
analyze_collected_running_config()
        |
        v
analyze_bytes()
        |
        v
parse_running_config()
        |
        v
AnalysisContext inmutable
        |
        v
RuleRegistry y reglas deterministas
        |
        v
RuleEvaluation para cada regla habilitada
        |
        +---- estado distinto de FAIL ----> sin Finding
        |
        +---- estado FAIL ----------------> Finding
```

La recopilación y la evaluación son etapas diferentes. La sesión SSH termina antes de que las reglas consuman el `AnalysisContext`.

## 5. Responsabilidad de los archivos

### `pyproject.toml`

Declara `netmiko>=4.7,<5` como dependencia de producción y mantiene Python 3.11 o superior. No incorpora dependencias de persistencia, TextFSM adicional, interfaz ni inteligencia artificial para este flujo.

### `src/ios_auditor/collectors/__init__.py`

Define la API pública del paquete de recopilación. Exporta la lista blanca, `NetmikoCollector`, `CommandEvidence` y las excepciones seguras que los consumidores pueden manejar sin importar detalles internos.

### `src/ios_auditor/collectors/netmiko_collector.py`

Contiene la conexión Netmiko, la validación previa de comandos, la ejecución en una única sesión, la creación de evidencias, la normalización de saltos de línea, el hash y el cierre seguro. No analiza reglas ni imprime resultados.

### `src/ios_auditor/services/__init__.py`

Conserva los puntos de entrada offline y publica el contrato y el servicio de integración SSH. No conecta este flujo con FastAPI ni con repositorios.

### `src/ios_auditor/services/ssh_analysis.py`

Implementa el orquestador de aplicación. Solicita exclusivamente `show running-config`, verifica la evidencia y su integridad, reutiliza `analyze_bytes()` y devuelve evidencia y análisis unidos sin almacenar el recolector.

### `tests/unit/test_netmiko_collector.py`

Prueba el recolector mediante `MagicMock`. Verifica la lista blanca, el uso de una sesión, la evidencia, la sanitización y la prohibición de métodos de configuración sin abrir una conexión real.

### `tests/unit/test_ssh_analysis.py`

Prueba la integración mediante recolectores falsos y analizadores inyectables. También ejecuta las tres reglas piloto con contenido ficticio, sin utilizar red ni credenciales reales.

## 6. Contratos y elementos implementados

### Recopilación

- `ALLOWED_COMMANDS`: `frozenset` que representa la lista blanca inmutable.
- `NetmikoConnection`: protocolo interno con las operaciones mínimas `send_command()` y `disconnect()`.
- `ConnectionFactory`: alias del callable utilizado para crear una conexión; permite inyectar mocks.
- `CollectorError`: excepción base segura del recolector.
- `CommandNotAllowedError`: indica que el comando no coincide exactamente con la lista blanca.
- `CollectorAuthenticationError`: representa un rechazo de autenticación sin revelar credenciales.
- `CollectorTimeoutError`: representa un timeout mediante un mensaje sanitizado.
- `CollectorConnectionError`: representa otros fallos seguros de sesión o cierre.
- `CommandEvidence`: dataclass inmutable con `slots` que conserva `execution_id`, `device_host`, comando, fecha UTC, salida original, salida normalizada y SHA-256. Las dos salidas se excluyen del `repr`.
- `NetmikoCollector`: dataclass que recibe host, puerto, usuario, contraseña y una fábrica de conexión. Usuario, contraseña y fábrica se excluyen del `repr`.
- `NetmikoCollector.collect()`: valida todos los comandos antes de conectar, reutiliza una sesión, crea una evidencia por comando y ejecuta `disconnect()` al terminar.
- `_normalize_line_endings()`: función interna que convierte CRLF y CR a LF sin cambiar el contenido técnico restante.

### Integración con el analizador

- `_RUNNING_CONFIG_COMMAND`: constante interna fijada en `show running-config`.
- `_SOURCE_NAME`: origen lógico interno `ssh-running-config`; no contiene el host.
- `RunningConfigCollector`: protocolo público mínimo que expresa solo el contrato `collect()` necesario por el orquestador.
- `_AnalysisCallable`: protocolo interno con la firma compatible con `analyze_bytes()` para permitir un analizador espía en pruebas.
- `CollectedAnalysisResult`: dataclass inmutable con `slots` que mantiene la `CommandEvidence` original y el `AnalysisResult`, sin copiar sus salidas a campos adicionales.
- `CollectedAnalysisResult.execution_id`: propiedad derivada de `evidence.execution_id`.
- `CollectedAnalysisContractError`: excepción segura para cardinalidad, tipo de evidencia, comando, UUID o hash incompatibles.
- `analyze_collected_running_config()`: función pública que recopila un único `show running-config`, valida el contrato, llama a `analyze_bytes()` y exige identidad entre el hash recopilado y el analizado.

## 7. Lista blanca de comandos

La lista blanca contiene exactamente:

- `show running-config`: fuente integrada con el analizador determinista.
- `show version`: consulta de plataforma y versión; todavía no se integra con reglas.
- `show ip interface brief`: consulta resumida de interfaces; su parsing estructurado queda pendiente.
- `show ip ssh`: consulta del estado SSH; su parsing estructurado queda pendiente.

La presencia en la lista blanca autoriza únicamente la recopilación. No implica que cada salida ya tenga parser o reglas asociadas.

## 8. Controles de seguridad

- Todos los comandos se normalizan con `strip()` y `lower()` antes de compararlos.
- La comparación posterior exige coincidencia exacta con la lista blanca.
- Pipes, argumentos adicionales, punto y coma y saltos de línea producen rechazo.
- La validación completa ocurre antes de crear la conexión de red.
- Varios comandos autorizados comparten una única sesión y un mismo `execution_id`.
- `disconnect()` se ejecuta incluso cuando falla un comando.
- Usuario y contraseña se excluyen del `repr` del recolector.
- `raw_output` y `normalized_output` se excluyen del `repr` de la evidencia.
- Los errores de autenticación, timeout, conexión y contrato utilizan mensajes sanitizados.
- El recolector no llama a `send_config_set()`, `config_mode()` ni a comandos de configuración.
- No existe aplicación automática de recomendaciones ni modificación de dispositivos.
- Las pruebas automatizadas usan fábricas inyectadas, mocks o recolectores falsos.

## 9. Decisión de integridad

`CommandEvidence.sha256` se calcula sobre `raw_output.encode("utf-8")`. El orquestador recalcula ese valor antes de analizar y entrega exactamente los mismos bytes a `analyze_bytes()`. Como `analyze_bytes()` calcula el SHA-256 de su entrada, `AnalysisResult.sha256` debe coincidir con el hash de la evidencia.

Después de verificar el contenido original, `parse_running_config()` divide y normaliza las líneas para crear el `AnalysisContext`. `normalized_output` permanece en `CommandEvidence` como representación trazable de saltos de línea normalizados, pero no sustituye el contenido original analizado.

## 10. Desacoplamiento arquitectónico

`NetmikoCollector` solo recopila. No importa reglas, no construye findings y no decide si una configuración cumple.

`analyze_collected_running_config()` coordina la frontera entre infraestructura y aplicación. El protocolo `RunningConfigCollector` permite sustituir el recolector por un falso durante las pruebas sin entregar Netmiko al motor.

Las reglas reciben únicamente `AnalysisContext`, que es inmutable. No conocen `NetmikoCollector`, SSH, usuario, contraseña, FastAPI, repositorios, base de datos ni inteligencia artificial. El mismo `analyze_bytes()` sostiene tanto el flujo en memoria como el flujo recopilado.

## 11. Pruebas unitarias del recolector

El recolector quedó respaldado por 19 pruebas unitarias con mocks. Estas comprueban:

- lista blanca exacta;
- ejecución de comandos autorizados;
- una sola sesión para varios comandos;
- rechazo antes de conectar;
- rechazo de pipes, argumentos y saltos de línea;
- UUID, fecha UTC, host lógico, salidas y SHA-256 de la evidencia;
- inmutabilidad;
- exclusión de credenciales y salidas del `repr`;
- cierre de sesión en éxito y error;
- traducción segura de autenticación y timeout;
- ausencia de métodos de configuración.

Estas pruebas no establecen conexiones con dispositivos.

## 12. Pruebas del servicio integrado

La integración agregó 18 pruebas con recolectores falsos, mocks y spies. Estas comprueban:

- solicitud única y exclusiva de `show running-config`;
- uso de `raw_output` y no de `normalized_output` como entrada del analizador;
- origen lógico sin host;
- propagación del registro opcional;
- conservación de evidencia, UUID y hash;
- ejecución de las tres reglas piloto;
- recepción de `AnalysisContext` por las reglas;
- rechazo de colecciones, comandos, UUID y hashes incompatibles;
- propagación intacta de errores seguros;
- mensajes sin contenido sensible;
- inmutabilidad del resultado;
- ausencia de red y métodos de configuración.

Estas pruebas tampoco realizan conexiones reales.

## 13. Evolución de la suite

- Después del recolector: 78 pruebas aprobadas.
- Después de la integración: 96 pruebas aprobadas.

La evolución confirma que se conservaron las pruebas de los incrementos anteriores y se añadieron coberturas específicas sin reemplazarlas.

## 14. Validación real inicial del recolector

La validación manual inicial se realizó contra un CSR1000v con IOS XE 16.9.5 ejecutado en VirtualBox. Se recopilaron los cuatro comandos autorizados en una única sesión, produciendo cuatro evidencias con un `execution_id` compartido. La configuración no se mostró en el registro documental y la conexión se cerró al finalizar.

Esta validación real fue manual y es distinta de las pruebas automatizadas con mocks. El registro no conserva dirección IP, usuario, credenciales, número de serie ni salidas del dispositivo.

## 15. Validación real integrada del 14 de julio de 2026

La validación manual integrada se realizó con el mismo CSR1000v IOS XE 16.9.5 ejecutado en VirtualBox, recopiló exclusivamente `show running-config` y produjo:

- coincidencia SHA-256: verdadera;
- tres evaluaciones;
- `IOS-ADM-001`: `PASS`;
- `IOS-SRV-001`: `PASS`;
- `IOS-AUTH-001`: `NOT_APPLICABLE`;
- cero findings;
- correspondencia entre evaluaciones `FAIL` y findings: verdadera;
- resultado final: `VALIDACION_INTEGRADA_OK`.

No se documenta el `running-config`, la dirección del laboratorio, credenciales, claves, certificados ni identificadores sensibles. Esta ejecución fue una validación manual previa; no forma parte de pytest.

## 16. Historial de implementación

- `3fac727`: implementación del recolector Netmiko de solo lectura.
- PR #1: revisión del recolector.
- `f18aa9d`: merge de la PR #1.
- `5366a3a`: integración del recolector con el analizador.
- PR #2: revisión de la integración.
- `abff23b`: merge de la PR #2.

Los commits y merges fueron verificados en el historial local del repositorio.

## 17. Limitaciones pendientes

- Solo `running-config` está integrado con el analizador determinista.
- Las salidas adicionales de comandos `show` aún no se estructuran con TextFSM.
- No existe persistencia mediante PostgreSQL, SQLAlchemy o Alembic.
- FastAPI todavía no expone recopilación SSH.
- No existe integración con inteligencia artificial.
- No hay `evidence_id` ni `analysis_id` persistentes para este flujo.
- `device_host` es el identificador de dispositivo disponible en esta etapa.
- La política definitiva de almacenamiento y rotación de credenciales sigue pendiente.

## 18. Decisiones oficiales resultantes

1. Netmiko es el recolector SSH de solo lectura para Cisco IOS e IOS XE en este incremento.
2. La lista blanca es inmutable y se valida antes de conectar.
3. El recolector produce evidencia y no ejecuta reglas.
4. `RunningConfigCollector` desacopla el servicio de la implementación concreta.
5. `analyze_collected_running_config()` es el orquestador del flujo integrado.
6. El análisis usa `raw_output` codificado en UTF-8 para conservar identidad de hash.
7. `normalized_output` se conserva como trazabilidad, no como sustituto del original.
8. Las reglas continúan recibiendo únicamente `AnalysisContext`.
9. El sistema no ejecuta cambios automáticos ni comandos de configuración.
10. FastAPI, persistencia e IA permanecen fuera de esta integración.

## 19. Utilidad para el Informe Técnico N.º 2

Este incremento aporta evidencia reutilizable para el Informe Técnico N.º 2 porque documenta una cadena completa y comprobable desde un dispositivo de red hasta evaluaciones deterministas. Permite explicar el diseño de solo lectura, la lista blanca, la trazabilidad criptográfica, el aislamiento de reglas, las pruebas con dobles de prueba y la validación manual controlada en laboratorio.

También permite diferenciar tres niveles de evidencia: contratos de código, pruebas automatizadas reproducibles y validaciones reales supervisadas. Esta separación fortalece la argumentación técnica sin exponer configuraciones ni datos sensibles del laboratorio.
