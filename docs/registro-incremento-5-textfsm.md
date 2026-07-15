# Registro técnico del Incremento 5: parsing de comandos show con TextFSM

## 1. Propósito del registro

Este documento describe el cierre del Incremento 5 del auditor de configuraciones Cisco IOS. Su objetivo es explicar, sin exigir conocimientos previos del proyecto, cómo las salidas de tres comandos `show` pasan de ser texto libre a convertirse en datos tipados, inmutables y utilizables por una regla determinista.

El incremento conserva el principio de solo lectura: recopila información, valida su integridad, la estructura y la evalúa, pero no modifica dispositivos.

## 2. Situación anterior

Al finalizar el Incremento 4, `NetmikoCollector` podía recopilar en una sola sesión SSH cuatro comandos autorizados y producir una `CommandEvidence` por cada salida. El flujo de `show running-config` ya estaba conectado al analizador determinista, pero las salidas de `show version`, `show ip interface brief` y `show ip ssh` permanecían como texto sin estructura.

Ese texto podía conservarse y verificarse mediante SHA-256, pero las reglas no debían interpretarlo directamente. Hacerlo habría mezclado parsing con evaluación y habría dificultado controlar variaciones de espacios, columnas y formatos entre versiones de Cisco IOS e IOS XE.

## 3. Texto sin estructura y datos estructurados

Una salida de consola sin estructura es una secuencia de líneas diseñada principalmente para lectura humana. La posición de una columna o la cantidad de espacios puede variar y los valores no tienen todavía un tipo explícito.

Los datos estructurados asignan nombres y tipos a los valores relevantes. Por ejemplo, una fila de interfaces se transforma en un objeto con nombre, dirección IP opcional, método, estado físico y estado del protocolo. De esta forma, una regla compara valores normalizados y no busca palabras dentro de la salida completa.

## 4. Responsabilidades de CiscoConfParse y TextFSM

`ciscoconfparse2`, mediante la clase `CiscoConfParse`, continúa siendo el parser oficial de `running-config`. Una configuración de Cisco IOS posee jerarquía basada en líneas principales e indentación, por lo que CiscoConfParse resulta apropiado para localizar secciones y sus comandos hijos.

TextFSM se utiliza para salidas tabulares o semiestructuradas de comandos `show`. Sus plantillas describen patrones de líneas y columnas y producen registros con campos nombrados. En este incremento se usa únicamente para:

- `show version`;
- `show ip interface brief`;
- `show ip ssh`.

`show running-config` no se procesa con TextFSM.

## 5. Motivo para no usar use_textfsm=True en Netmiko

No se utiliza `use_textfsm=True` dentro de `NetmikoCollector` porque el recolector tiene una sola responsabilidad: ejecutar comandos autorizados y conservar evidencia. Si Netmiko realizara también el parsing, la recopilación quedaría acoplada a plantillas, modelos y decisiones de normalización.

La separación implementada permite:

- probar el parser sin abrir conexiones;
- conservar la salida original aunque el parsing falle;
- cambiar o validar plantillas sin modificar el recolector;
- impedir que las reglas conozcan Netmiko o SSH;
- reproducir el parsing a partir de una evidencia previamente recopilada.

## 6. Separación de responsabilidades

El flujo distingue seis responsabilidades:

1. **Recopilación:** `NetmikoCollector` ejecuta únicamente comandos de la lista blanca.
2. **Evidencia:** `CommandEvidence` conserva comando, ejecución, dispositivo, fecha UTC, salida original, salida normalizada y hash.
3. **Validación de integridad:** `parse_collected_show_evidence()` recalcula SHA-256 y verifica la normalización.
4. **Parsing:** `parse_show_command()` selecciona una plantilla TextFSM y crea un modelo tipado.
5. **Contexto operacional:** `OperationalContext` conserva trazabilidad y datos estructurados sin incluir la salida completa.
6. **Regla:** `IOS-IF-001` recibe exclusivamente el contexto operacional y produce una `RuleEvaluation`.

## 7. Flujo completo implementado

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
modelo tipado e inmutable
        |
        v
OperationalContext
        |
        v
IOS-IF-001
        |
        v
RuleEvaluation
```

La sesión SSH termina antes del parsing y de la evaluación. El parser y la regla no abren conexiones.

## 8. Dependencia y recursos

TextFSM se declaró como dependencia directa de producción:

```text
textfsm>=2.1,<3
```

Esto evita depender accidentalmente de que Netmiko lo instale de manera transitiva. Las plantillas se mantienen dentro de `src/ios_auditor/resources/textfsm/` y se incluyen como datos del paquete mediante `pyproject.toml`. El comportamiento queda así versionado, auditable y reproducible.

## 9. Archivos creados

- `src/ios_auditor/parsers/show_commands.py`: parser público, normalización, selección de plantillas, errores seguros y conversión a modelos.
- `src/ios_auditor/services/operational_analysis.py`: validación de `CommandEvidence` y construcción de `OperationalContext`.
- `src/ios_auditor/rules/operational.py`: implementación y carga controlada de `IOS-IF-001`.
- `src/ios_auditor/resources/rules/IOS-IF-001.yaml`: metadatos oficiales de la regla operacional.
- `src/ios_auditor/resources/textfsm/__init__.py`: paquete de recursos TextFSM.
- `cisco_ios_show_version.textfsm`: plantilla para versión, plataforma, imagen y uptime.
- `cisco_ios_show_ip_interface_brief.textfsm`: plantilla estricta para filas de interfaces.
- `cisco_ios_show_ip_ssh.textfsm`: plantilla para estado y parámetros de SSH.
- `tests/unit/test_show_command_parser.py`: 12 pruebas del parser y modelos.
- `tests/unit/test_operational_analysis.py`: 9 pruebas del servicio y la trazabilidad.
- `tests/unit/test_operational_rule.py`: 7 pruebas de la regla operacional.

## 10. Archivos modificados

- `pyproject.toml`: dependencia directa de TextFSM y empaquetado de plantillas.
- `src/ios_auditor/domain/models.py`: modelos operacionales inmutables.
- `src/ios_auditor/parsers/__init__.py`: API pública del parsing de comandos `show`.
- `src/ios_auditor/services/__init__.py`: API pública del servicio operacional.
- `src/ios_auditor/rules/__init__.py`: API pública de la primera regla operacional.

No se modificaron `NetmikoCollector`, el parser de `running-config`, el analizador offline, FastAPI ni la CLI.

## 11. Modelos operacionales

### InterfaceStatus

Enumeración de estados normalizados de interfaz: `up`, `down`, `administratively down` y `deleted`. Los espacios internos de `administratively down` se normalizan antes de crear el valor.

### ProtocolStatus

Enumeración del protocolo de línea, con valores `up` y `down`.

### ShowVersionData

Conserva versión de IOS o IOS XE, familia o plataforma cuando puede determinarse, imagen de software opcional y uptime opcional. No contiene hostname ni número de serie.

### InterfaceBriefEntry

Representa una interfaz mediante nombre, dirección IP opcional, método opcional, estado de interfaz y estado de protocolo.

### ShowIpInterfaceBriefData

Agrupa las interfaces en una tupla inmutable. La dirección `unassigned` se representa como ausencia de dirección IP.

### ShowIpSshData

Indica si SSH aparece habilitado, la versión informada y, cuando están presentes, timeout y cantidad de reintentos de autenticación.

### OperationalContext

Une los datos estructurados con `execution_id`, identificador lógico del dispositivo, comando, fecha UTC y SHA-256. Es una dataclass con `frozen=True` y `slots=True`. No contiene `raw_output`, `normalized_output`, credenciales ni objetos de conexión.

## 12. Funciones, constantes y excepciones

### parse_show_command()

Normaliza el comando mediante `strip()` y `lower()`, exige que pertenezca al conjunto soportado, rechaza salidas vacías, carga la plantilla asociada y convierte los registros en un modelo tipado. No abre conexiones ni imprime información.

### normalize_show_output()

Convierte saltos CRLF y CR a LF sin alterar el contenido técnico restante.

### SUPPORTED_SHOW_COMMANDS

Es un mapeo inmutable entre los tres comandos soportados y sus plantillas. No incluye `show running-config`.

### parse_collected_show_evidence()

Recibe una `CommandEvidence`, valida comando, SHA-256, correspondencia entre salida original y normalizada y fecha UTC. Después entrega al parser únicamente el comando y la salida normalizada y construye el contexto operacional.

### OperationalEvidenceError

Indica que una evidencia incumple el contrato, por ejemplo por hash alterado, comando no soportado, normalización inconsistente o fecha sin UTC. Sus mensajes no contienen la salida ni datos de conexión.

### OperationalAnalysisError

Representa hacia el consumidor un fallo seguro al estructurar la evidencia. No revela la salida que causó el error.

### InterfaceLineProtocolRule

Implementa la lógica determinista de `IOS-IF-001`. Solo conoce modelos de dominio, metadatos y resultados de reglas; no importa Netmiko.

### get_interface_operational_rule()

Carga de manera controlada el YAML de `IOS-IF-001`, comprueba su identificador y conserva en caché la instancia inmutable.

## 13. Plantillas TextFSM

### show version

Extrae versión de IOS o IOS XE y, cuando aparecen con el formato soportado, plataforma, imagen de software y uptime. La plantilla no define un campo para números de serie, direcciones MAC, claves o certificados, por lo que esos datos no llegan al modelo.

### show ip interface brief

Extrae nombre, dirección IP, método, estado y protocolo. Reconoce `up`, `down`, `administratively down` y `deleted`. Una regla de error rechaza filas desconocidas para impedir que una salida parcialmente reconocida sea aceptada como completa.

### show ip ssh

Extrae estado habilitado o deshabilitado, versión SSH y parámetros de autenticación cuando están presentes. En la validación disponible reconoció el formato de IOS XE 16.9.5.

## 14. Datos deliberadamente excluidos

El incremento no extrae ni entrega a las reglas:

- contraseñas o nombres de usuario;
- números de serie;
- hostname real del dispositivo;
- claves SSH o privadas;
- certificados;
- salida completa de comandos;
- `running-config`;
- objetos de conexión Netmiko.

La regla de interfaces tampoco incluye direcciones IP en su evidencia: registra solamente nombre de interfaz y estados normalizados.

## 15. Integridad, UUID e inmutabilidad

`CommandEvidence.sha256` se calcula sobre `raw_output.encode("utf-8")`. El servicio operacional aplica exactamente el mismo cálculo antes de parsear. También verifica que `normalized_output` corresponda a la normalización de la salida original.

El `execution_id` se conserva desde la evidencia hasta `OperationalContext`. Cuando varios comandos se recopilan en una sesión, las evidencias comparten el mismo UUID. Los modelos utilizan dataclasses congeladas y la colección de interfaces es una tupla, por lo que las reglas no pueden modificarlas.

## 16. Funcionamiento exacto de IOS-IF-001

La regla se denomina **Interfaz físicamente activa con protocolo de línea inactivo** y tiene severidad `MEDIUM`.

- `FAIL`: existe al menos una interfaz con estado `up` y protocolo distinto de `up`.
- `PASS`: existe al menos una interfaz evaluable y ninguna presenta esa inconsistencia.
- `NOT_APPLICABLE`: el contexto no corresponde a `show ip interface brief`.
- `NOT_EVALUATED`: no existen interfaces evaluables.

Una interfaz `administratively down` se excluye porque puede haber sido deshabilitada intencionalmente. Marcarla como incumplimiento produciría falsos positivos. La regla no audita SSH y la observación de una versión SSH no afecta su resultado.

La evidencia de un `FAIL` contiene solamente el nombre de la interfaz, su estado y su protocolo. No contiene dirección IP ni salida original.

## 17. Posibles falsos positivos y limitaciones de la regla

Una combinación `up/down` puede ser transitoria durante convergencia, inicialización o una prueba controlada. Por esa razón, la recomendación exige revisar el enlace, la encapsulación y ambos extremos antes de aplicar cambios.

La regla no diagnostica por sí sola la causa del estado, no ejecuta comandos adicionales y no modifica la interfaz.

## 18. Pruebas automatizadas

El incremento agregó 28 pruebas:

- 12 del parser, las plantillas y los modelos;
- 9 del servicio operacional y la trazabilidad;
- 7 de `IOS-IF-001`.

La evolución de la suite fue:

- 96 pruebas antes del Incremento 5;
- 122 después de la primera implementación;
- 124 después de agregar dos pruebas de regresión;
- 124 aprobadas después del merge.

Las pruebas usan salidas ficticias y sanitizadas. No abren conexiones, no llaman `ConnectHandler` y no ejecutan métodos de configuración.

## 19. Segunda revisión técnica

La segunda revisión encontró dos defectos reales:

1. Los espacios múltiples dentro de `administratively down` podían impedir reconocer una fila válida.
2. Una fila con un estado desconocido podía omitirse silenciosamente si otras filas sí coincidían, generando un resultado parcial.

Las correcciones fueron:

- permitir espacios variables en la plantilla y normalizarlos antes de construir `InterfaceStatus`;
- validar la cabecera y rechazar cualquier fila de interfaz no reconocida;
- traducir los errores de datos TextFSM a `ShowOutputFormatError` sanitizado.

Las dos pruebas de regresión confirman la normalización de espacios múltiples y el rechazo completo, sin filtrar la fila problemática.

## 20. Validación real controlada

La validación manual se realizó contra un CSR1000v con IOS XE 16.9.5 ejecutado en VirtualBox. No se utilizó GNS3. GNS3 queda como posible ampliación futura si se dispone legalmente de imágenes IOSv o IOSvL2 autorizadas; actualmente no se dispone de ellas.

El resultado sanitizado fue:

- tres evidencias recopiladas;
- un único `execution_id`;
- hashes SHA-256 correctos;
- tres modelos generados;
- una interfaz evaluable;
- cero inconsistencias `up/down`;
- `IOS-IF-001`: `PASS`;
- sesión cerrada correctamente;
- resultado final `VALIDACION_TEXTFSM_OK`.

No se registra la dirección del laboratorio, usuario, contraseña, hostname, salidas completas, direcciones de interfaces ni identificadores sensibles.

Durante una comprobación previa, un host incorrecto produjo `CollectorTimeoutError` con un mensaje sanitizado. El valor introducido no se documentó.

## 21. Observación sobre SSH 1.99

La validación mostró SSH 1.99. Esta observación se conserva únicamente como candidato para estudiar una regla futura específica de versión SSH. No es un incumplimiento de `IOS-IF-001`, no produjo un finding en este incremento y no motivó cambios en el dispositivo.

Antes de implementar una regla de este tipo deberán definirse condición, severidad, excepciones, evidencia, referencias y pruebas independientes.

## 22. Seguridad y solo lectura

- Solo se recopilaron los tres comandos `show` estructurados por este incremento.
- No se ejecutaron `send_config_set()`, `config_mode()`, `configure terminal` ni comandos equivalentes.
- No se aplicaron recomendaciones ni cambios automáticos.
- Las credenciales se suministraron únicamente durante la validación manual y no aparecen en el repositorio o este registro.
- La sesión se cerró antes de mostrar los resultados sanitizados.
- Parsers y reglas permanecen sin acceso a red.

## 23. Limitaciones pendientes

- Solo tres comandos `show` poseen parsing estructurado.
- Existe una sola regla operacional.
- El servicio procesa una evidencia por llamada.
- FastAPI no procesa ni expone resultados operacionales.
- No existe persistencia para evidencias o contextos operacionales.
- No existe integración con inteligencia artificial.
- Las plantillas se validaron únicamente con las variantes disponibles.
- No existe todavía un registro general unificado para reglas de configuración y operacionales.

## 24. Control de versiones

- Rama de implementación: `feature/textfsm-show-parsing`.
- Commit de implementación: `0ca7cf3`.
- Pull Request: #4.
- Merge en la rama principal: `b7be551`.

## 25. Utilidad para el Informe Técnico N.º 3

Este incremento permite explicar y demostrar una cadena completa desde evidencia de red hasta una evaluación operacional determinista. Aporta material para documentar selección de parsers, diseño de plantillas, tipado, inmutabilidad, integridad criptográfica, pruebas sin red, corrección de defectos y validación supervisada en laboratorio.

También permite diferenciar evidencia original, datos estructurados y evaluación técnica, evitando presentar el parsing o la inteligencia artificial como si fueran la fuente del hallazgo.

## 26. Glosario básico

- **Comando show:** consulta que presenta el estado o información de un dispositivo sin cambiar su configuración.
- **Parsing:** transformación de texto en datos identificables y utilizables por software.
- **TextFSM:** herramienta que aplica plantillas a texto para producir registros con campos.
- **Plantilla:** conjunto de patrones que describe cómo reconocer valores en una salida.
- **Modelo tipado:** estructura cuyos campos y tipos están definidos explícitamente.
- **Inmutable:** objeto que no puede modificarse después de ser creado.
- **Contexto operacional:** conjunto normalizado de datos obtenidos del estado del dispositivo y su trazabilidad.
- **Evidencia:** información original y metadatos que permiten justificar y reproducir un análisis.
- **SHA-256:** función criptográfica utilizada para detectar cambios en el contenido.
- **UUID o execution_id:** identificador único de una ejecución de recopilación.
- **Regla determinista:** condición explícita que produce el mismo resultado ante el mismo contexto.
- **Falso positivo:** resultado que marca un problema aunque la condición observada sea legítima o transitoria.

## 27. Conclusión

El Incremento 5 queda completado con tres parsers TextFSM reproducibles, modelos y contexto operacional inmutables, validación de integridad y la regla `IOS-IF-001`. Las 124 pruebas permanecen aprobadas y la validación real confirmó el flujo sin exponer datos sensibles ni modificar el dispositivo.

La próxima etapa no queda fijada automáticamente. Deberá decidirse entre ampliar reglas operacionales, integrar resultados operacionales con FastAPI, incorporar persistencia o preparar una capa explicativa de inteligencia artificial después de ampliar la base de reglas.
