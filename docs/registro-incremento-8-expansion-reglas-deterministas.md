# Registro técnico del Incremento 8: expansión de reglas deterministas

## 1. Identificación del incremento

| Campo | Valor |
|---|---|
| Incremento | 8 |
| Nombre | Ampliación controlada del catálogo determinista de `running-config` |
| Rama de implementación | `feature/deterministic-rule-expansion` |
| Commit de definición | `54cf2b0` — `docs: define increment 8 deterministic rule expansion` |
| Commit de referencias | `cdf2cd8` — `docs: add official references for increment 8 rules` |
| Commit de implementación | `89270a1` — `feat: expand deterministic running-config rules` |
| Estado | Implementado, probado y validado |
| Resultado integral | Siete reglas de configuración y una regla operacional |

Este documento registra el cierre técnico del Incremento 8. La implementación, las pruebas automatizadas y la validación real se mantuvieron separadas: las pruebas utilizaron datos sintéticos y dobles de prueba, mientras que la validación real se ejecutó una sola vez mediante el flujo SSH oficial de solo lectura.

## 2. Situación inicial

Al finalizar el Incremento 7, el análisis integral ya proporcionaba:

- una sesión SSH de solo lectura;
- cuatro comandos canónicos;
- cuatro `CommandEvidence` con un `execution_id` común;
- parsing de `running-config` mediante `ciscoconfparse2` y `CiscoConfParse`;
- tres `OperationalContext` construidos mediante TextFSM;
- tres reglas de configuración registradas en `RuleRegistry`;
- `IOS-IF-001` como regla operacional separada;
- cuatro evaluaciones integrales;
- findings derivados exclusivamente de evaluaciones `FAIL`;
- una respuesta API tipada y sanitizada.

El contrato integral estaba estabilizado, pero el catálogo seguía limitado a tres reglas de `running-config`. El incremento debía ampliar ese catálogo sin cambiar las fuentes, la recopilación SSH, los parsers ni el endpoint.

## 3. Objetivo

Agregar cuatro reglas deterministas basadas exclusivamente en `running-config`:

- `IOS-ADM-002`: control de versión SSH;
- `IOS-SRV-002`: servicios TCP/UDP pequeños;
- `IOS-NTP-001`: configuración de servidor NTP;
- `IOS-LOG-001`: configuración de Syslog remoto.

El objetivo funcional fue aumentar de cuatro a ocho las evaluaciones del análisis integral, manteniendo el orden determinista, los contextos inmutables, la evidencia mínima, la sanitización y la relación exacta entre `FAIL` y `Finding`.

## 4. Alcance implementado

- Cuatro clases de reglas en Python.
- Cuatro archivos YAML de metadatos.
- Ampliación explícita de `OFFICIAL_RULE_FILES` y `RULE_TYPES`.
- Orden oficial de siete reglas de `running-config`.
- Reutilización de `AnalysisContext` sin modificar su contrato.
- Conservación de `IOS-IF-001` sobre `OperationalContext`.
- Evidencia mínima y sanitizada.
- Cobertura de precedencias, formas negadas, coincidencias, sintaxis incompletas y ambigüedades.
- Actualización de expectativas de servicios, CLI, API y análisis integral.
- Pruebas automatizadas sin conexiones reales.
- Validación real controlada y sanitizada contra una CSR1000v autorizada.

## 5. Elementos fuera del alcance

El incremento no incorporó:

- nuevos comandos `show`;
- cambios en la lista blanca;
- cambios en Netmiko, SSH o TextFSM;
- cambios en los endpoints;
- nuevas dependencias;
- PostgreSQL, SQLAlchemy o Alembic;
- Streamlit;
- reportes automáticos;
- pasarela de inteligencia artificial;
- GNS3 o nuevas imágenes Cisco;
- reglas OSPF, SNMP, consola o nomenclatura;
- cambios automáticos en dispositivos;
- persistencia de evidencias reales;
- gestión definitiva de credenciales.

## 6. Decisiones técnicas conservadas

El incremento mantuvo las siguientes decisiones:

1. La lógica de evaluación reside en Python.
2. YAML conserva únicamente metadatos declarativos.
3. Las reglas reciben contextos normalizados e inmutables.
4. Las reglas no reciben conexiones, credenciales ni objetos Netmiko.
5. Las reglas no acceden a FastAPI, persistencia o inteligencia artificial.
6. Todas las evaluaciones se conservan.
7. Solo `FAIL` genera findings.
8. Una excepción inesperada produce `ERROR`, nunca un resultado técnico falso.
9. Las fuentes originales permanecen separadas: CiscoConfParse para `running-config` y TextFSM para comandos `show`.
10. `IOS-IF-001` conserva su cargador y contexto operacional separados.

Las decisiones generales se mantienen en [decisiones-tecnicas.md](decisiones-tecnicas.md), [arquitectura.md](arquitectura.md), [catalogo-reglas.md](catalogo-reglas.md) y [plan-incremental.md](plan-incremental.md).

## 7. Diseño de la ampliación determinista

La ampliación se implementó en [`increment8.py`](../src/ios_auditor/rules/increment8.py). Cada clase:

- declara un `expected_id`;
- recibe un `RuleMetadata` inmutable;
- implementa `evaluate(context)`;
- devuelve una `RuleEvaluation`;
- utiliza exclusivamente `AnalysisContext`;
- no modifica el contexto;
- no ejecuta entrada/salida ni conexiones.

El flujo resultante es:

```text
running-config
      |
      v
CiscoConfParse
      |
      v
AnalysisContext inmutable
      |
      v
RuleRegistry
      |
      +--> IOS-ADM-001
      +--> IOS-SRV-001
      +--> IOS-AUTH-001
      +--> IOS-ADM-002
      +--> IOS-SRV-002
      +--> IOS-NTP-001
      +--> IOS-LOG-001
      |
      v
RuleEvaluation
      |
      +--> FAIL ----------> Finding
      |
      +--> otros estados -> sin Finding
```

El análisis integral agrega después `IOS-IF-001`, evaluada sobre el `OperationalContext` correspondiente a `show ip interface brief`.

## 8. IOS-ADM-002: control de versión SSH

| Propiedad | Contrato |
|---|---|
| Severidad | `HIGH` |
| Fuente | `running-config` |
| `FAIL` | Existe la directiva activa y exacta `ip ssh version 1` |
| `PASS` | Existe `ip ssh version 2` y no existe la versión 1 |
| `NOT_EVALUATED` | No existe una versión SSH explícita |

La regla exige coincidencia exacta de tokens. Una forma negada o una línea con tokens adicionales no se interpreta como la directiva aprobada. Si aparecen las versiones 1 y 2, la versión 1 prevalece y el resultado es `FAIL`.

La evidencia `FAIL` contiene únicamente `ip ssh version 1` y el número de línea. La evidencia `PASS` es sintética. No se incluyen claves, material criptográfico ni salida de `show ip ssh`.

## 9. IOS-SRV-002: servicios TCP/UDP pequeños

| Propiedad | Contrato |
|---|---|
| Severidad | `MEDIUM` |
| Fuente | `running-config` |
| `FAIL` | Existe `service tcp-small-servers` o `service udp-small-servers` |
| `PASS` | No existe ninguna directiva activa |
| `NOT_APPLICABLE` | No se utiliza |

La comparación exige los tokens base exactos y permite conservar argumentos opcionales de una directiva válida. Textos similares, comentarios y nombres extendidos no coinciden. Las formas `no service tcp-small-servers` y `no service udp-small-servers` no generan `FAIL`.

Si ambas directivas están activas, la evaluación conserva dos evidencias mínimas en el orden original. No se agregan líneas vecinas.

## 10. IOS-NTP-001: servidor NTP

| Propiedad | Contrato |
|---|---|
| Severidad | `MEDIUM` |
| Fuente | `running-config` |
| `PASS` | Existe al menos una directiva `ntp server` activa, completa y reconocida |
| `FAIL` | No existe un servidor NTP válido |

La regla reconoce destinos directos y variantes con `vrf`, `ip` o `ipv6`. No confunde palabras de opciones como `prefer`, `key`, `source` o `version` con un destino. Las formas negadas, incompletas o sin destino producen `FAIL` conforme al contrato de entrada de una configuración completa.

La evidencia nunca conserva el destino:

- `PASS`: `servidor NTP: configurado`;
- `FAIL`: `servidor NTP: no configurado`.

## 11. IOS-LOG-001: servidor Syslog remoto

| Propiedad | Contrato |
|---|---|
| Severidad | `MEDIUM` |
| Fuente | `running-config` |
| `PASS` | Existe un destino remoto con sintaxis reconocida |
| `FAIL` | No existe destino remoto ni sintaxis remota ambigua |
| `NOT_EVALUATED` | Existe una posible sintaxis remota que no puede clasificarse con seguridad |

La regla admite:

- sintaxis moderna `logging host <destino> [opciones soportadas]`;
- sintaxis heredada inequívoca `logging <destino>`.

Las directivas locales, como `logging buffered`, `logging console`, `logging monitor`, `logging trap`, `logging facility` y `logging source-interface`, no se consideran destinos. Las formas negadas tampoco configuran un destino activo.

Una sintaxis potencialmente remota pero desconocida produce `NOT_EVALUATED`; esta decisión evita transformar una ambigüedad en un falso `FAIL`.

La evidencia es sintética:

- `PASS`: `servidor Syslog remoto: configurado`;
- `FAIL`: `servidor Syslog remoto: no configurado`.

No se conservan destino, VRF, dirección, hostname, transporte, puerto u opciones.

## 12. Estados de evaluación

El motor conserva los cinco estados del dominio:

| Estado | Significado |
|---|---|
| `PASS` | La regla pudo evaluarse y el control cumple |
| `FAIL` | La regla detectó un incumplimiento |
| `NOT_APPLICABLE` | El control no corresponde al escenario evaluado |
| `NOT_EVALUATED` | La información o sintaxis no permite una conclusión fiable |
| `ERROR` | Ocurrió un fallo inesperado durante la evaluación |

No todas las reglas necesitan producir todos los estados. La ausencia de un estado en una regla concreta es parte de su contrato, no una sustitución silenciosa.

## 13. Precedencias, negaciones y ambigüedades

Las decisiones principales son:

- SSH versión 1 prevalece sobre versión 2.
- SSH requiere coincidencia exacta y no presume seguro un valor predeterminado.
- Las formas negadas de SSH, servicios pequeños, NTP y Syslog no cuentan como configuración activa.
- Los servicios pequeños rechazan nombres similares que solo contienen el texto esperado.
- NTP exige un destino y distingue opciones de destino.
- Syslog separa destinos remotos de directivas locales.
- Syslog usa `NOT_EVALUATED` ante una sintaxis potencialmente remota no reconocida.
- Las excepciones internas se convierten en `ERROR` mediante el analizador y no en `PASS`, `FAIL` o `NOT_EVALUATED`.

## 14. Evidencia mínima y sanitizada

La evidencia de las reglas nuevas sigue cuatro criterios:

1. Conservar únicamente la directiva insegura necesaria cuando un fragmento literal es indispensable.
2. Usar evidencia sintética cuando la presencia o ausencia puede demostrarse sin revelar valores.
3. No incluir líneas vecinas de configuración.
4. No exponer destinos, hostnames, direcciones, claves, VRF u opciones sensibles.

`IOS-ADM-002` y `IOS-SRV-002` conservan solo directivas inseguras pertinentes. `IOS-NTP-001` e `IOS-LOG-001` usan textos sintéticos tanto para presencia como para ausencia.

## 15. Metadatos y referencias oficiales

Cada regla posee un YAML con:

- ID y versión;
- nombre y categoría;
- descripción;
- severidad predeterminada;
- fuente requerida;
- plataformas aplicables;
- riesgo;
- recomendación;
- referencias oficiales;
- falsos positivos;
- excepciones;
- estado de habilitación.

Las fuentes oficiales registradas son:

- Cisco IOS XE 17.x — Secure Shell Version 2 Support;
- Cisco IOS XE 17.x — Performing Basic System Management;
- Cisco IOS XE 17.x — Network Time Protocol;
- Cisco IOS Embedded Syslog Manager Command Reference — `logging host`;
- Cisco IOS XE 17.17.x — Configuring System Message Logs.

Los enlaces se encuentran en [catalogo-reglas.md](catalogo-reglas.md) y en los cuatro YAML bajo [`resources/rules`](../src/ios_auditor/resources/rules/).

## 16. Integración con RuleRegistry

[`registry.py`](../src/ios_auditor/rules/registry.py) declara explícitamente siete archivos y siete tipos:

1. `IOS-ADM-001`
2. `IOS-SRV-001`
3. `IOS-AUTH-001`
4. `IOS-ADM-002`
5. `IOS-SRV-002`
6. `IOS-NTP-001`
7. `IOS-LOG-001`

El registro conserva el orden de `RULE_TYPES`, valida la identidad entre clase y YAML, rechaza duplicados y solo entrega reglas habilitadas. El flujo integral concatena después la evaluación operacional `IOS-IF-001`.

## 17. AnalysisContext y OperationalContext

Las siete reglas de configuración comparten el `AnalysisContext` inmutable derivado de `show running-config` o de una entrada local equivalente. Ninguna recibe la conexión, las credenciales o una salida operacional.

`IOS-IF-001` continúa recibiendo un `OperationalContext` construido a partir de `show ip interface brief`. No se unificaron ambos contratos ni se trasladó la regla operacional al registro de configuración.

## 18. Evaluaciones y findings

`findings_from_evaluations()` deriva un `Finding` exclusivamente cuando `RuleStatus` es `FAIL`. El incremento conservó esta transformación sin añadir rutas alternativas.

Por lo tanto:

- `PASS` se conserva como evaluación y no genera finding;
- `FAIL` se conserva y genera exactamente un finding;
- `NOT_APPLICABLE` se conserva y no genera finding;
- `NOT_EVALUATED` se conserva y no genera finding;
- `ERROR` se conserva y no genera finding.

El contrato también es validado por `FullDeviceAnalysisResult` y por el transformador de la respuesta integral.

## 19. Cambios realizados

### Lógica y metadatos

| Archivo o grupo | Cambio |
|---|---|
| `src/ios_auditor/rules/increment8.py` | Implementación de las cuatro reglas |
| `src/ios_auditor/rules/registry.py` | Ampliación del orden y archivos oficiales |
| `src/ios_auditor/resources/rules/IOS-ADM-002.yaml` | Metadatos SSH |
| `src/ios_auditor/resources/rules/IOS-SRV-002.yaml` | Metadatos de servicios pequeños |
| `src/ios_auditor/resources/rules/IOS-NTP-001.yaml` | Metadatos NTP |
| `src/ios_auditor/resources/rules/IOS-LOG-001.yaml` | Metadatos Syslog |

### Pruebas y compatibilidad

| Grupo | Responsabilidad |
|---|---|
| `tests/unit/test_increment8_rules.py` | Estados, precedencias, negaciones, sintaxis y sanitización |
| Metadatos y registro | Siete YAML, contratos, orden y reglas deshabilitadas |
| Servicios y findings | Nuevos conteos y correspondencia exclusiva desde `FAIL` |
| CLI y muestras | Compatibilidad con siete evaluaciones de configuración |
| API de archivos e integral | Resúmenes y ocho evaluaciones sin cambiar endpoints |
| Orquestaciones SSH simuladas | Siete reglas de configuración y una operacional |

### Documentación previa a la implementación

- `AGENTS.md`;
- `docs/arquitectura.md`;
- `docs/catalogo-reglas.md`;
- `docs/decisiones-tecnicas.md`;
- `docs/plan-incremental.md`.

## 20. Estrategia de pruebas

La validación automatizada avanzó desde reglas aisladas hacia consumidores integrales:

1. Casos dirigidos iniciales.
2. Corrección y revisión individual de cada regla.
3. Reglas, metadatos y registro.
4. Servicios, CLI y orquestaciones simuladas.
5. Contratos y API.
6. Suite completa antes del commit.
7. Suite completa después del commit.

Los grupos parciales se superponen. No deben sumarse para inferir el total de pruebas.

## 21. Resultados de pruebas automatizadas

| Ejecución | Resultado |
|---|---:|
| Pruebas iniciales dirigidas | `34 passed` |
| Primera revisión individual | `15 passed` |
| Segunda revisión individual | `16 passed` |
| Tercera revisión individual | `16 passed` |
| Cuarta revisión individual | `14 passed` |
| Reglas corregidas, metadatos y registro | `63 passed` |
| Servicios, CLI y orquestaciones simuladas | `68 passed` |
| Contratos y API | `88 passed` |
| Suite completa antes del commit | `314 passed` |
| Suite completa después del commit | `314 passed` |

Resultado oficial de la suite:

- `passed`: 314;
- `failed`: 0;
- `skipped`: 0;
- `xfailed`: 0;
- warnings de pytest: 0.

Las pruebas no abrieron SSH, no ejecutaron comandos reales, no iniciaron Uvicorn y no dependieron de la CSR1000v.

## 22. Auditorías estáticas y Git

Antes de la validación real se confirmó:

- rama `feature/deterministic-rule-expansion`;
- HEAD `89270a1a31a9d96d2b546f332c8f6a1cfe472cd8`;
- `main` en `f405f57f46f2fc9e04b78ce529bfe974fa530f3d`;
- presencia de los tres commits del Incremento 8;
- árbol limpio;
- ausencia de cambios, push, Pull Request o merge del incremento.

Las revisiones incluyeron inspección del diff, estados de Git, formato de hashes y búsqueda de información sensible. El cierre documental se realiza en un commit separado de la implementación.

## 23. Procedimiento de validación real

La validación utilizó el procedimiento oficial ya empleado por el proyecto:

- punto de entrada público `collect_and_analyze_device()`;
- `NetmikoCollector`;
- fábrica real instrumentada para contar conexión, comandos y desconexión;
- variables de entorno transitorias;
- salida limitada a contadores, estados e identificadores autorizados;
- ninguna persistencia de salidas o evidencias reales.

La presencia de las variables se comprobó solo mediante booleanos:

```text
HOST_CONFIGURADO=True
USUARIO_CONFIGURADO=True
CONTRASENA_CONFIGURADA=True
PUERTO_CONFIGURADO=True
```

El precheck manual sanitizado, conservado externamente, confirmó:

```text
ICMP_DISPONIBLE=True
SSH_TCP_DISPONIBLE=True
```

## 24. Incidentes procedimentales

La secuencia se documenta para conservar trazabilidad:

1. Un primer precheck automatizado se detuvo al fallar aisladamente la conectividad básica.
2. Una comprobación manual posterior confirmó de forma sanitizada ICMP y TCP/SSH disponibles para el mismo destino configurado.
3. Dos invocaciones locales del validador fallaron durante el arranque: una por `SyntaxError` y otra por `ImportError`.
4. Ambos fallos ocurrieron antes de leer las variables de conexión o invocar Netmiko.
5. Corregido el arranque local, se realizó la única validación SSH real.

Estos eventos no representan defectos funcionales del motor. Hubo exactamente una conexión y una validación SSH real.

## 25. Resultado real sanitizado

| Comprobación | Resultado |
|---|---:|
| Conexión SSH | Exitosa |
| Plataforma genérica | Cisco IOS/IOS XE |
| Sesiones creadas | 1 |
| Desconexiones | 1 |
| Comandos registrados | 4 |
| Evidencias recolectadas | 4 |
| Lote validado | Correcto |
| Contextos operacionales | 3 |
| Evaluaciones | 8 |
| Findings | 2 |
| `execution_id` | Válido y común a las cuatro evidencias |

Los comandos registrados, exactamente en este orden, fueron:

1. `show running-config`
2. `show version`
3. `show ip interface brief`
4. `show ip ssh`

Durante la validación integral no se ejecutaron ping, `Test-NetConnection`, pytest, `enable`, `configure terminal`, comandos de escritura, Uvicorn ni una solicitud HTTP real.

## 26. Evaluaciones reales

| Orden | Regla | Contexto | Estado |
|---:|---|---|---|
| 1 | `IOS-ADM-001` | `AnalysisContext` | `PASS` |
| 2 | `IOS-SRV-001` | `AnalysisContext` | `PASS` |
| 3 | `IOS-AUTH-001` | `AnalysisContext` | `NOT_APPLICABLE` |
| 4 | `IOS-ADM-002` | `AnalysisContext` | `NOT_EVALUATED` |
| 5 | `IOS-SRV-002` | `AnalysisContext` | `PASS` |
| 6 | `IOS-NTP-001` | `AnalysisContext` | `FAIL` |
| 7 | `IOS-LOG-001` | `AnalysisContext` | `FAIL` |
| 8 | `IOS-IF-001` | `OperationalContext` | `PASS` |

Resumen:

- `PASS`: 4;
- `FAIL`: 2;
- `NOT_APPLICABLE`: 1;
- `NOT_EVALUATED`: 1;
- `ERROR`: 0.

Los ocho IDs fueron únicos y el orden coincidió con `RuleRegistry` más la regla operacional. `IOS-ADM-002` quedó `NOT_EVALUATED` porque no existía una directiva explícita de versión SSH; esto es el comportamiento conservador definido y no un fallo del motor.

## 27. Findings reales

| ID | Severidad |
|---|---|
| `IOS-NTP-001` | `MEDIUM` |
| `IOS-LOG-001` | `MEDIUM` |

La correspondencia fue exacta:

- cada `FAIL` produjo un finding;
- ningún `PASS`, `NOT_APPLICABLE`, `NOT_EVALUATED` o `ERROR` produjo findings;
- no hubo findings adicionales ni ausentes.

Los findings indican ausencia de los controles requeridos. El registro no revela valores ni destinos.

## 28. Sanitización comprobada

La validación programática confirmó:

- DTO de resumen sanitizado;
- ausencia de host, usuario, contraseña y secretos;
- ausencia de `running-config` completo;
- ausencia de salidas originales y normalizadas completas;
- ausencia de direcciones de interfaces;
- ausencia de contextos operacionales completos;
- destinos NTP no revelados;
- destinos Syslog no revelados;
- UUID y hashes con formato contractual;
- hashes no impresos;
- evidencias completas no impresas;
- invocación exclusiva de los cuatro comandos canónicos.

Las salidas reales existieron únicamente en memoria durante el flujo oficial y no se incorporaron al repositorio.

## 29. Seguridad y garantía de solo lectura

La garantía de no modificación se sustenta en:

- lista blanca fija;
- exactamente cuatro llamadas registradas a `send_command()`;
- ausencia de `enable`;
- ausencia de `configure terminal`;
- ausencia de `send_config_set()`, `config_mode()` u otros métodos de configuración;
- una sesión y una desconexión;
- flujo dedicado exclusivamente a recopilación.

No se efectuó una comparación invasiva del estado de la CSR1000v antes y después. La conclusión de no modificación se apoya en la instrumentación, la lista blanca y la ausencia de rutas de escritura, no en una intervención adicional sobre el dispositivo.

## 30. Evidencias gráficas externas

Las capturas sanitizadas se conservan fuera del repositorio para su eventual incorporación al informe técnico.

| Evidencia | Descripción prevista |
|---|---|
| Precheck sanitizado | Comprobación sanitizada de conectividad ICMP y disponibilidad del servicio SSH de la CSR1000v. |
| Resumen integral | Resumen sanitizado de la validación integral real del Incremento 8. |

Antes de incorporarlas al informe deberá verificarse nuevamente que no contengan direcciones, credenciales, hostnames, configuraciones ni salidas completas.

## 31. Limitaciones

- La validación real utilizó una sola CSR1000v autorizada.
- `IOS-ADM-002` no pudo determinar una versión SSH explícita.
- `IOS-NTP-001` y `IOS-LOG-001` produjeron findings reales por ausencia del control requerido.
- Los destinos NTP y Syslog no fueron revelados.
- La no modificación se acredita mediante instrumentación, lista blanca y ausencia de métodos de configuración.
- No se efectuó una comparación invasiva antes y después del estado del dispositivo.
- Las capturas del precheck y del resumen se conservan externamente.
- Los estados alternativos están cubiertos por pruebas automatizadas, pero no necesariamente aparecieron en la única CSR real.
- Las variantes futuras de sintaxis Cisco pueden requerir ampliaciones controladas y nuevas pruebas.
- El catálogo integral contiene ocho reglas, todavía por debajo del catálogo objetivo del MVP.

## 32. Criterios de aceptación

| Criterio | Resultado |
|---|---|
| Cuatro reglas Python y cuatro YAML | Cumplido |
| Siete reglas de configuración en orden | Cumplido |
| Ocho evaluaciones integrales | Cumplido |
| Contextos separados | Cumplido |
| Evidencia mínima y sanitizada | Cumplido |
| Negaciones y ambigüedades controladas | Cumplido |
| Excepciones inesperadas representables como `ERROR` | Cumplido |
| Findings exclusivamente desde `FAIL` | Cumplido |
| Compatibilidad con CLI, servicios y API | Cumplido |
| Suite completa con 314 pruebas | Cumplido |
| Validación real de solo lectura | Cumplido |
| Sin nuevas fuentes, comandos o dependencias | Cumplido |
| Sin exposición de datos sensibles | Cumplido |

## 33. Aporte al proyecto

El incremento demuestra que el catálogo puede crecer sin debilitar las fronteras arquitectónicas. La lógica nueva se integra mediante contratos existentes, mantiene resultados deterministas y extiende la auditoría hacia administración remota, reducción de superficie de ataque, sincronización horaria y registro remoto.

La combinación de pruebas sintéticas y una validación real única permite separar cobertura lógica de demostración operacional. Los resultados reales no se forzaron: incluyeron cumplimiento, incumplimiento, no aplicabilidad y falta de información explícita.

## 34. Conclusión

El Incremento 8 demostró que el catálogo determinista puede ampliarse sobre los contratos existentes sin alterar la arquitectura, la lista blanca, los parsers, los endpoints ni las dependencias. Las reglas nuevas conservaron la separación de contextos, la evidencia mínima y la correspondencia exclusiva entre `FAIL` y findings, mientras que la validación de solo lectura confirmó su integración sin modificar el dispositivo.

## 35. Próxima etapa

No existe una siguiente etapa aprobada o numerada. PostgreSQL, Streamlit, reportes, inteligencia artificial y nuevas reglas continúan como alternativas pendientes de evaluación.

Una decisión futura deberá definir alcance, riesgos, criterios de aceptación y validaciones antes de autorizar implementación. Este registro no convierte ninguna alternativa en un incremento oficial.

## 36. Glosario

| Término | Definición |
|---|---|
| `AnalysisContext` | Contexto inmutable derivado de `running-config` para las siete reglas de configuración |
| `OperationalContext` | Contexto inmutable derivado de un comando `show` estructurado |
| `RuleRegistry` | Registro ordenado que asocia clases Python y metadatos YAML |
| `RuleEvaluation` | Resultado completo de una regla, cualquiera sea su estado |
| Finding | Hallazgo derivado exclusivamente de una evaluación `FAIL` |
| Evidencia sintética | Texto controlado que demuestra una condición sin revelar el valor real |
| Precedencia | Regla que determina qué condición domina cuando existen directivas conflictivas |
| Forma negada | Directiva iniciada por `no` que desactiva o elimina una configuración |
| Ambigüedad | Sintaxis potencialmente relevante que no permite una clasificación segura |
| `NOT_EVALUATED` | Estado utilizado cuando falta información suficiente para concluir |
| `ERROR` | Estado reservado para un fallo inesperado de evaluación |
| `CommandEvidence` | Evidencia inmutable de un comando autorizado |
| `execution_id` | UUID común que relaciona evidencias y resultados de una ejecución |
| DTO | Objeto de transferencia con únicamente los datos autorizados |
| Solo lectura | Flujo que consulta información sin ingresar a configuración ni escribir en el dispositivo |
