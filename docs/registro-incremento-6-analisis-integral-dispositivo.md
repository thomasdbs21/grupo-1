# Registro técnico del Incremento 6: análisis integral del dispositivo

## 1. Identificación y propósito

Este documento registra el cierre funcional del **Incremento 6 — Orquestación multifuente y análisis integral del dispositivo**. El incremento integra capacidades ya implementadas para producir una auditoría inmutable y trazable a partir de una única sesión SSH de solo lectura, sin trasladar responsabilidades de infraestructura a los parsers o a las reglas.

El cierre se sustenta en revisión de código, historial Git, 197 pruebas automatizadas y una validación manual sanitizada contra un dispositivo virtual autorizado.

## 2. Situación inicial

Al comenzar el incremento ya estaban disponibles:

- `NetmikoCollector`, con lista blanca y cierre seguro de una sesión SSH;
- el análisis de `show running-config` mediante `ciscoconfparse2` y `CiscoConfParse`;
- los parsers TextFSM para `show version`, `show ip interface brief` y `show ip ssh`;
- `AnalysisContext` y `OperationalContext` como contratos inmutables separados;
- las tres reglas de configuración y la regla operacional `IOS-IF-001`;
- servicios independientes para analizar configuración y cada evidencia operacional.

Todavía no existían un contrato agregado de auditoría, una validación estricta del conjunto de cuatro evidencias ni un servicio que coordinara recopilación y análisis en una única operación.

## 3. Objetivo y alcance

El objetivo fue construir un flujo integral que:

1. abra una sola sesión SSH mediante `NetmikoCollector`;
2. recopile exactamente cuatro fuentes autorizadas;
3. valide su cardinalidad, identidad, temporalidad, normalización e integridad;
4. reutilice los analizadores existentes de configuración y datos operacionales;
5. ejecute cuatro reglas deterministas;
6. conserve todas las evaluaciones;
7. derive hallazgos únicamente de evaluaciones `FAIL`;
8. devuelva un `FullDeviceAnalysisResult` inmutable.

El alcance incluyó el contrato de dominio integral, el lote validado, el orquestador puro, la integración SSH, errores sanitizados, pruebas sin red y validación manual controlada.

## 4. Elementos fuera del alcance

No se incorporaron:

- PostgreSQL, SQLAlchemy ni Alembic;
- Streamlit ni nuevos endpoints SSH de FastAPI;
- pasarela de inteligencia artificial;
- nuevos comandos `show` o nuevas reglas;
- unificación general de todos los registros de reglas;
- gestión definitiva de credenciales;
- cambios automáticos en dispositivos;
- GNS3, nuevas imágenes Cisco o validación simultánea de varios dispositivos.

## 5. Decisiones técnicas conservadas

- La recopilación pertenece al collector; el parsing y las reglas no abren conexiones.
- CiscoConfParse procesa exclusivamente `running-config`.
- TextFSM procesa exclusivamente los tres comandos `show` operacionales soportados.
- Las reglas reciben contextos normalizados e inmutables, nunca credenciales ni objetos Netmiko.
- `rule_evaluations` conserva todos los estados y `findings` contiene únicamente resultados derivados de `FAIL`.
- El sistema permanece estrictamente en modo de solo lectura.
- Los errores públicos no incluyen salidas, credenciales ni datos internos del dispositivo.

## 6. Componentes implementados

### 6.1 FullDeviceAnalysisResult

`FullDeviceAnalysisResult` compone, sin mezclar sus contratos internos:

- el `execution_id` común;
- las cuatro `CommandEvidence`;
- el `AnalysisResult` de configuración;
- tres `OperationalContext`;
- evaluaciones y findings operacionales.

Sus propiedades `evaluations` y `findings` agregan los resultados de configuración y operacionales. La dataclass es inmutable y valida que los findings correspondan exactamente a evaluaciones `FAIL`.

### 6.2 ValidatedEvidenceBatch

`ValidatedEvidenceBatch` exige una tupla con exactamente una evidencia por comando canónico. Rechaza comandos ausentes, duplicados, adicionales o no autorizados, tipos incompatibles, UUID distintos, fechas no UTC, hashes inválidos y normalización inconsistente. También ordena las evidencias canónicamente sin reconstruirlas.

### 6.3 Orquestador puro

`analyze_validated_evidence_batch()` no abre conexiones. Recibe únicamente un lote validado, analiza `show running-config`, construye tres contextos operacionales, ejecuta `IOS-IF-001` sobre el contexto de interfaces y devuelve el resultado integral.

### 6.4 Integración SSH

`collect_and_analyze_device()` construye un único `NetmikoCollector`, solicita las cuatro evidencias en una llamada, valida el lote una vez y entrega por identidad ese mismo lote al orquestador puro. No reconstruye evidencias ni resultados.

## 7. API pública cerrada

```python
collect_and_analyze_device(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    connection_factory: ConnectionFactory | None = None,
) -> FullDeviceAnalysisResult
```

La fábrica inyectable permite pruebas sin red. Cuando no se proporciona, `NetmikoCollector` utiliza la fábrica real de Netmiko. La función devuelve directamente el `FullDeviceAnalysisResult` producido por `analyze_validated_evidence_batch()`.

## 8. Sesión SSH y comandos canónicos

La sesión se administra exclusivamente dentro de `NetmikoCollector.collect()`. La integración realiza una llamada a ese método y no abre una segunda conexión. El collector crea la conexión, ejecuta los comandos y llama a `disconnect()` en su bloque de cierre, incluso ante errores posteriores a la creación de la sesión.

Los comandos se ejecutan una vez y en este orden:

1. `show running-config`;
2. `show version`;
3. `show ip interface brief`;
4. `show ip ssh`.

La lista no se duplica en el nuevo servicio: se reutiliza `CANONICAL_EVIDENCE_COMMANDS`.

## 9. UUID, evidencia e integridad

La integración genera una sola vez el `execution_id` mediante `uuid4()` y lo entrega a `NetmikoCollector.collect()`. Las cuatro evidencias conservan ese mismo UUID.

Cada `CommandEvidence` se construye mediante `_collect_command()` dentro del collector e incluye comando, origen lógico, `collected_at`, salida original, salida normalizada y SHA-256. `collected_at` es consciente de zona horaria y representa UTC.

La normalización convierte CRLF y CR a LF sin modificar el resto del contenido técnico. El hash se calcula exactamente como:

```python
hashlib.sha256(raw_output.encode("utf-8")).hexdigest()
```

El SHA-256 no se calcula sobre `normalized_output`. La salida normalizada se valida por separado contra la normalización oficial de la salida original.

## 10. Validación y conservación por identidad

`validate_evidence_batch()` se invoca una vez en la integración. El objeto `ValidatedEvidenceBatch` devuelto se entrega por identidad a `analyze_validated_evidence_batch()`. Las evidencias se conservan como los objetos originales y el resultado integral se devuelve directamente, sin crear lotes o resultados parciales alternativos.

La validación ocurre después de que `NetmikoCollector.collect()` ha cerrado la sesión. Por ello, si falla la validación o el análisis, no queda una conexión abierta.

## 11. Parsing y contextos operacionales

`show running-config` se entrega como bytes UTF-8 al analizador existente basado en CiscoConfParse. Los otros comandos producen tres contextos mediante las plantillas TextFSM versionadas:

- `cisco_ios_show_version.textfsm` → `ShowVersionData`;
- `cisco_ios_show_ip_interface_brief.textfsm` → `ShowIpInterfaceBriefData`;
- `cisco_ios_show_ip_ssh.textfsm` → `ShowIpSshData`.

Cada `OperationalContext` conserva UUID, fuente lógica, comando, fecha UTC, SHA-256 y datos tipados. No contiene salidas completas, credenciales ni conexiones.

## 12. Reglas deterministas ejecutadas

El flujo ejecuta exactamente estas cuatro reglas:

- `IOS-ADM-001` — **Telnet permitido en líneas VTY**: detecta secciones VTY que permiten Telnet; puede producir `PASS`, `FAIL` o `NOT_EVALUATED` según la información disponible.
- `IOS-SRV-001` — **Servidor HTTP sin cifrado habilitado**: produce `FAIL` cuando existe exactamente `ip http server`; en caso contrario produce `PASS`.
- `IOS-AUTH-001` — **Enable password sin enable secret**: produce `FAIL` ante `enable password` sin `enable secret`, `PASS` si existe `enable secret` y `NOT_APPLICABLE` si no existe ninguno.
- `IOS-IF-001` — **Interfaz físicamente activa con protocolo de línea inactivo**: evalúa `show ip interface brief` y produce `FAIL` cuando una interfaz está `up` con protocolo distinto de `up`; también contempla `PASS`, `NOT_APPLICABLE` y `NOT_EVALUATED`.

Las tres primeras se ejecutan mediante el `RuleRegistry` de configuración. `IOS-IF-001` se carga separadamente mediante `get_interface_operational_rule()` y se ejecuta una vez sobre el contexto de interfaces.

## 13. Evaluaciones y findings

Una `RuleEvaluation` registra el resultado de cada regla y puede tener estado `PASS`, `FAIL`, `NOT_APPLICABLE`, `NOT_EVALUATED` o `ERROR`. Un `Finding` representa únicamente un incumplimiento derivado de una evaluación `FAIL`.

El resultado integral conserva cuatro evaluaciones: tres de configuración y una operacional. La validación manual produjo cero findings. Esto demuestra que ninguna de las cuatro evaluaciones fue `FAIL`; no permite afirmar por sí solo que todas hayan sido `PASS`, porque los contratos admiten otros estados que tampoco generan findings.

## 14. Compatibilidad

La integración no modifica la firma ni el comportamiento de `NetmikoCollector.collect()`. Tampoco altera `analyze_collected_running_config()`, que continúa disponible para recopilar y analizar únicamente `show running-config`. El nuevo flujo compone contratos existentes en lugar de reemplazarlos.

## 15. Errores y sanitización

Se conservan las excepciones públicas del collector para autenticación, timeout, conexión y comandos no autorizados. El lote utiliza `EvidenceBatchValidationError`; el orquestador puro utiliza errores seguros de análisis y `FullDeviceAnalysisContractError`.

Los mensajes no incorporan `str()` ni `repr()` de errores internos sensibles, salidas, credenciales o datos reales del dispositivo. Un fallo detiene el flujo y no devuelve un `FullDeviceAnalysisResult` parcial. La política preexistente de desconexión se conserva: un fallo al cerrar después de una operación exitosa se informa mediante un error seguro; si ya existía un fallo operacional, el error original mantiene prioridad.

## 16. Garantías de solo lectura

- Solo se envían los cuatro comandos canónicos de consulta.
- No se utilizan `send_config_set()`, `config_mode()`, `enable()` ni comandos de configuración.
- La envoltura de validación manual expuso únicamente `send_command()` y `disconnect()`.
- Parsers, contextos y reglas no conocen Netmiko ni credenciales.
- El incremento no guarda ni aplica recomendaciones en el dispositivo.

## 17. Historial Git verificado

El historial funcional del Incremento 6 contiene cuatro commits:

- `f7e4398` — `feat: add full device analysis result contract`;
- `ae832dd` — `feat: add strict evidence batch validation`;
- `92d82fd` — `feat: add pure full device analysis orchestration`;
- `5753768` — `feat: add full device SSH analysis orchestration`.

Cada bloque cerró un contrato independiente antes de integrar la conexión real.

## 18. Pruebas automatizadas

El incremento agregó 73 casos pytest:

- 14 para `FullDeviceAnalysisResult`;
- 27 para `ValidatedEvidenceBatch`;
- 20 para el orquestador puro;
- 12 para la integración SSH integral.

La suite pasó de 124 a 197 casos, todos aprobados. Las pruebas usan objetos sintéticos, mocks y fábricas inyectadas; no abren conexiones reales.

La cantidad de casos pytest no equivale a la cantidad de comportamientos conceptuales. La parametrización genera casos separados para estados, comandos o posiciones de fallo, mientras que un caso de integración puede comprobar conjuntamente sesión, orden, evidencia, UUID, parsing, reglas y cierre.

Entre los comportamientos cubiertos se encuentran inmutabilidad, agregación, ausencia o duplicación de fuentes, validación UTC, normalización, SHA-256, errores sanitizados, ejecución única de reglas y parsers, identidad de objetos, una sola sesión, fallos independientes en las cuatro posiciones y ausencia de métodos de configuración.

## 19. Metodología de validación manual

La validación se realizó manualmente una sola vez el **22-07-2026** contra una **CSR1000v IOS XE 16.9.5 ejecutada en VirtualBox**. Se utilizó un validador temporal fuera del repositorio que invocó exclusivamente la API pública `collect_and_analyze_device()` e instrumentó la fábrica real para contar conexiones, comandos y desconexiones.

Las credenciales y parámetros de conexión se solicitaron de forma interactiva y oculta. El validador no imprimió ni almacenó configuraciones, salidas, evidencias, hostname, seriales, hashes completos o datos de acceso. El árbol Git permaneció limpio y el HEAD `5753768` se conservó antes y después.

## 20. Resultado sanitizado de la validación real

La ejecución confirmó:

- conexiones creadas: 1;
- desconexiones: 1;
- comandos canónicos: 4/4 y en orden;
- evidencias válidas: 4/4;
- `execution_id` común: correcto;
- fechas UTC: correctas;
- normalización: correcta;
- SHA-256 sobre `raw_output` codificado en UTF-8: correcto;
- lote validado: correcto;
- contextos operacionales: 3/3;
- `IOS-IF-001`: ejecutada una vez;
- evaluaciones: 4;
- findings: 0;
- correspondencia exclusiva entre `FAIL` y findings: correcta;
- `FullDeviceAnalysisResult`: correcto;
- operación exclusivamente de lectura: correcta;
- resultado final: `VALIDACION_CSR1000V: OK`.

La suite previa contenía 197 pruebas aprobadas. No se documentan estados individuales no conservados en el resultado sanitizado.

## 21. Evidencia académica externa

Las capturas de la terminal integrada de VS Code constituyen evidencia académica externa y sanitizada de la fecha, rama, HEAD, limpieza del árbol y resultado del validador. No se copiaron imágenes al repositorio. Su conservación y eventual incorporación al Informe Técnico N.º 4 requieren una autorización separada y una revisión previa de datos visibles.

## 22. Seguridad de credenciales y datos

Este registro no incluye dirección de red, host, usuario, contraseña, configuración, salidas originales o normalizadas, fragmentos de evidencia, hostname, número de serie, hashes completos, claves, certificados ni tokens.

Las credenciales existieron únicamente en memoria durante la ejecución manual. El validador presentó solo contadores y estados sanitizados y no activó logging de Netmiko.

## 23. Limitaciones actuales

- La validación real se realizó sobre una sola CSR1000v.
- El flujo integral admite exactamente cuatro comandos canónicos.
- El catálogo integral sigue limitado a tres reglas de configuración y una operacional.
- No se validaron simultáneamente múltiples dispositivos reales.
- Los fallos reales en cada posición de comando no se provocaron contra el dispositivo; esas rutas se verificaron principalmente con conexiones simuladas.
- El validador manual fue temporal y no forma parte de la interfaz del producto.
- No existe modificación automática de dispositivos.
- PostgreSQL, Streamlit, nuevos endpoints SSH, reportes ampliados e inteligencia artificial permanecen pendientes de decisión o implementación futura.
- Las variantes reales comprobadas se limitan a la plataforma y versión disponibles en el laboratorio autorizado.

## 24. Aporte al proyecto de título

El incremento demuestra una cadena técnica completa desde adquisición controlada hasta evaluación determinista: una sesión, cuatro fuentes verificables, dos estrategias de parsing, contextos inmutables, cuatro reglas y un resultado agregado. Esto permite explicar académicamente separación de responsabilidades, integridad criptográfica, trazabilidad, pruebas sin infraestructura real y validación supervisada de solo lectura.

También estabiliza el contrato sobre el que podrán diseñarse persistencia, visualización y reportes, evitando definir almacenamiento antes de conocer la forma completa de una auditoría.

## 25. Próxima etapa

El Incremento 6 queda funcionalmente completado. No se declara automáticamente un Incremento 7. PostgreSQL, Streamlit, reportes, ampliación del catálogo, nuevos endpoints e inteligencia artificial continúan como alternativas pendientes de evaluación y aprobación formal.

## 26. Glosario

- **Auditoría integral:** resultado que compone configuración, datos operacionales, evaluaciones y findings de una misma ejecución.
- **CommandEvidence:** evidencia inmutable producida por un comando autorizado.
- **ValidatedEvidenceBatch:** lote de cuatro evidencias cuya cardinalidad, orden, UUID, fecha, normalización e integridad fueron validados.
- **FullDeviceAnalysisResult:** contrato inmutable que agrega los resultados de configuración y operacionales.
- **execution_id:** UUID común que relaciona las evidencias y resultados de una ejecución.
- **Contexto operacional:** representación tipada de una salida `show`, sin conexión ni salida completa.
- **Evaluación:** resultado estructurado de una regla, cualquiera sea su estado.
- **Finding:** hallazgo creado exclusivamente desde una evaluación `FAIL`.
- **SHA-256:** función criptográfica usada para comprobar que la salida original no cambió.
- **Solo lectura:** operación que consulta el dispositivo sin entrar al modo de configuración ni aplicar cambios.

## 27. Conclusión técnica

El Incremento 6 queda funcionalmente cerrado con un contrato integral inmutable, validación estricta de cuatro evidencias, reutilización de los analizadores existentes, cuatro reglas deterministas y una integración SSH de una sola sesión. Las 197 pruebas y la validación manual sanitizada confirmaron el flujo, su trazabilidad y las garantías de solo lectura sin exponer información sensible.
