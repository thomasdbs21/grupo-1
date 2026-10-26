# Auditoría transversal 4→8: Evaluación 2

Fecha: 1 de octubre de 2026. Rama feature/evaluacion-2-validacion.
HEAD inicial c78570f0b204d11ea8172b4cb452e10fa4e7b7f6; sin commit, push ni SSH real.

## Puerta previa a las tres reglas

Estado inicial verificado: 37 archivos del diff, incluidos intent-to-add ya
existentes, más 31 archivos sin seguimiento: **68 archivos reales**. Staging
sin contenido. Se revisaron los 31, no solo los nombres de directorios agregados
que muestra git status por defecto. Todo pertenece a la campaña autorizada.

El código no conservaba un consumidor integral limitado a cuatro. Se corrigieron
instrucciones documentales vigentes obsoletas en registro-evaluacion-2-validacion:
wrapper, permisos, contador de consultas y capturas. También se aclaró el corte
estático en catálogo. Los resultados históricos de cuatro comandos se conservaron.

Antes de añadir reglas: **607 passed, 1 warning in 7.00s**, suite completa offline.
Incluye dos nuevas comprobaciones transversales: acuerdo entre allowlist, orden,
Literal API, parsers y cardinalidad OpenAPI; rechazo público del payload antiguo
de cuatro evidencias. Warning externo de Starlette/AnyIO visible, no ocultado.
No se encontró problema arquitectónico serio que impidiera continuar.

## Consumidores examinados

| Consumidor | Resultado de revisión |
|---|---|
| ALLOWED_COMMANDS / CANONICAL_EVIDENCE_COMMANDS | Exactamente los mismos ocho; orden canónico explícito, sin comandos arbitrarios. |
| NetmikoCollector / CommandEvidence | Valida antes de conectar; una fábrica/sesión, consultas send_command, finally/disconnect, originales y SHA-256/UTC. CommandEvidence representa un comando, no un lote de cuatro. |
| ValidatedEvidenceBatch | Cardinalidad derivada de la tupla canónica, identidad preservada al ordenar, duplicados/ausencias/adicionales/UUID/hash/normalización/UTC rechazados. Un lote antiguo de cuatro es inválido. |
| collect_and_analyze_device | Una collect con toda la tupla; una validación y un análisis puro, sin unpacking de cuatro. |
| analyze_validated_evidence_batch | Lookup por comando; siete parejas comando/modelo y siete contextos. No posiciones fijas de las cuatro fuentes iniciales. |
| Parsing | CiscoConfParse para configuración y siete plantillas TextFSM. Las cuatro nuevas distinguen formato reconocido de desconocido; NTP/OSPF descartan destinos en los nuevos modelos. |
| FullDeviceAnalysisResult | Colecciones inmutables y agregado dinámico. No fija número de fuentes o reglas: el lote se valida en la frontera del servicio y el DTO vuelve a exigir ocho metadatos. |
| API schemas / mapper / app | Literal exacto de ocho; minItems/maxItems derivados; mapper ya usa canónico dinámico y valida UUID/findings. App delega una vez, rutas y payloads sin cambios. |
| Wrapper manual | Orden y total derivados del canónico, una sesión/intento, entrada oculta, sin persistir ni imprimir datos sensibles. Sin ejecución real. |
| Campaña / offline_integral | Construye ocho evidencias en memoria recorriendo el canónico; análisis público, expectativas explícitas y contadores calculados, sin transporte SSH. |
| Tests integrales | Transporte simulado, ocho consultas en orden, desconexión, rechazo previo, hashes/UTC, DTO sanitizado y finding si y solo si FAIL. Tests antiguos preservados. |

## Clasificación de referencias a cuatro

La búsqueda incluyó palabras cuatro/four, literal 4, len, índices, slices y
consumidores del contrato. Las ubicaciones siguientes corresponden a la inspección
inicial, antes de editar documentos; se agrupan todas las apariciones con la misma
clasificación y razón. A histórico válido; B otro significado; C migrar; D deuda.

| Ubicación inicial | Clase | Tratamiento |
|---|---|---|
| registros Incrementos 4, 5, 6, 7, 8: todas sus menciones de cuatro consultas/evidencias, diagramas y resultados reales | A | Sin cambios: describen el contrato y validaciones de esos cortes. |
| arquitectura 446, 465–468, 485; plan-incremental 136, 158, 216, 257, 278, 297, 359 | A | Historia de Incrementos 4–8, no flujo vigente EV2; conservada. |
| decisiones-tecnicas 136, 200, 237–238, 251, 258, 269, 327 | A | Decisiones y validaciones históricas conservadas. |
| registro-expansion-reglas 56; registro-expansion-operacional 12, 90 | A | Corte estático previo y reemplazo explícito del lote antiguo. Ahora enlazan al corte vigente, sin cambiar sus cifras. |
| registro-evaluacion-2-validacion 67 | A | Las pruebas iniciales ejercitaron cuatro comandos; no fingir ocho retrospectivamente. |
| registro-evaluacion-2-validacion: wrapper/lista canónica actual, contador, permisos de lectura (118) y capturas 36/12 presentadas como vigentes | C | Corregido a ocho consultas y cifras calculadas vigentes; se distingue wrapper inicial. |
| AGENTS 132, 601, 615 | A | Historia de Incrementos 6/8, conservada. |
| AGENTS 139, contexto actual y sección 14 con lista de cuatro | D documental | Generalización antigua: se conserva el archivo intacto por la revisión previa; la autorización explícita EV2 y los registros actuales sustituyen ese contrato para esta rama. Reconciliar instrucciones generales antes de un cierre oficial, sin alterar la historia. |
| AGENTS 623; decisiones-tecnicas 348; definición Incremento 9 23, 203, 251, 260, 266, 369, 391, 414 | D futura | Especificación aprobada pero no implementada de cuatro evidencias. Requiere decisión de compatibilidad antes de persistencia; no es un consumidor ejecutable ni se implementa aquí. |
| tests/unit/test_full_device_api_contracts.py:236, total_evaluations==4 | B | Fixture deliberadamente mínima de evaluaciones, con ocho evidencias: prueba mapper dinámico, no cardinalidad integral actual. |
| tests de servicio/SSH/integración API: cuatro findings | B | Cuatro incumplimientos reales en esas fixtures; no son evidencias y no cambian por añadir fuentes. |
| test_operational_expansion: lote canónico[:4] | B | Prueba negativa: el contrato histórico debe rechazarse. |
| test_evidence_batch: evidences[2], [0], [3], [1], *evidences[4:] | B | Permutación de las ocho evidencias para verificar identidad y orden, no unpacking de cuatro. |
| run_validation_scenarios: cuatro FAIL operacionales; test_evaluacion_2_validation: cuatro NOT_EVALUATED estáticos | B | Expectativas declaradas de controles concretos, no cantidad de comandos. |
| VTY 0 4, fecha/minutos 4, zona UTC−4, NTP version 4 | B | Valores de sintaxis/datos de prueba ajenos a cardinalidad. |
| evaluation2/evaluation2_operational: len(tokens)==4, tokens[4:], bindings[4], ACL cuatro tokens | B | Gramática de comandos de configuración, no colección de evidencias. |
| parents[2], contextos/evaluaciones/evidence[0], rules metadata[0], parser rows[0] | B | Raíz de rutas, primer registro o primera evidencia; no contrato de cuatro. |
| índices de regla futura en test_full_device_api | B / mejora | Son posiciones de evaluaciones, no de fuentes. Se actualizan conservando la aserción del ID y el orden completo del sufijo operacional, no eliminándola. |

No se encontró unpacking de exactamente cuatro evidencias. El único lookup
posicional del lote usa CANONICAL_EVIDENCE_COMMANDS.index(command), calculado
sobre la tupla completa, y existe cobertura para cada uno de sus ocho elementos.
El servicio antiguo collect_and_analyze_running_config sigue recopilando UNA
fuente por diseño; es un análisis de configuración, no un consumidor integral.

## Los 31 untracked iniciales revisados

- Un registro operacional: docs/registro-expansion-operacional-evaluacion-2.md.
- samples/evaluacion_2/operacional/README.md y quince fixtures: para seguro,
  inseguro y no_evaluable, show_interfaces.txt, show_access_lists.txt,
  show_ip_interface_brief.txt, show_ntp_associations.txt, show_ip_ospf_neighbor.txt.
- scripts/evaluacion_2/offline_integral.py.
- domain/operational_sources.py y parsers/operational_show.py bajo src/ios_auditor.
- Cinco YAML: IOS-INT-002, IOS-ACL-002, IOS-NTP-002, IOS-AVL-001, IOS-OSPF-002.
- Cuatro TextFSM: show_interfaces, show_access_lists, show_ntp_associations,
  show_ip_ospf_neighbor, con prefijo cisco_ios_ y extensión .textfsm.
- rules/evaluation2_operational.py y tests/unit/test_operational_expansion.py.

Todos son texto del alcance EV2; modelos/plantillas/reglas no abren SSH, las
fixtures son sintéticas y el script público no usa transporte. No hay credenciales
reales, IA, base de datos, archivos binarios ni dependencias nuevas en este lote.

Deuda no bloqueante adicional: se construye dos veces AnalysisContext en el
orquestador para preservar los contratos de servicios existentes; no duplica lógica
de reglas, solo coste de parsing. Compatibilidad real de plantillas y comandos con
CSR1000v pendiente; las simulaciones no prueban acceso ni comportamiento real.

## Corte final y Git

Después de esta puerta se incorporaron los controles descritos en
[registro actual](registro-controles-adicionales-evaluacion-2.md).
La revisión de archivos se contabiliza mediante git diff --numstat más
git ls-files --others --exclude-standard y git diff --no-index --numstat NUL archivo.
No se utiliza staging para hacer aparecer untracked en estadísticas.
git diff --check se complementa con --no-index --check para cada archivo nuevo;
el exit 1 de una comparación nueva significa diferencia, no error de whitespace.
La rama y HEAD permanecen sin commit; AGENTS, dependencias y registros históricos
de Incrementos 0–9 no se modifican. No hay SSH real, push, PR, merge ni rebase.

### Inventario final de archivos para revisión

Salida de git status --short --untracked-files=all desde la raíz Git. Los A en
segunda columna son intent-to-add preexistentes, no contenido staged. El diff
cached sigue vacío. Total: 77 archivos, 37 del diff y 40 sin seguimiento.

~~~text
 M Proyecto-Titulo-Cisco-IOS/README.md
 M Proyecto-Titulo-Cisco-IOS/docs/arquitectura.md
 M Proyecto-Titulo-Cisco-IOS/docs/catalogo-reglas.md
 A Proyecto-Titulo-Cisco-IOS/docs/registro-evaluacion-2-validacion.md
 A Proyecto-Titulo-Cisco-IOS/docs/registro-expansion-reglas-evaluacion-2.md
 A Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/README.md
 A Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/escenario_inseguro.cfg
 A Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/escenario_no_evaluable.cfg
 A Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/escenario_seguro.cfg
 A Proyecto-Titulo-Cisco-IOS/scripts/evaluacion_2/run_csr1000v_validation.py
 A Proyecto-Titulo-Cisco-IOS/scripts/evaluacion_2/run_validation_scenarios.py
 M Proyecto-Titulo-Cisco-IOS/src/ios_auditor/api/schemas.py
 M Proyecto-Titulo-Cisco-IOS/src/ios_auditor/collectors/netmiko_collector.py
 M Proyecto-Titulo-Cisco-IOS/src/ios_auditor/domain/models.py
 M Proyecto-Titulo-Cisco-IOS/src/ios_auditor/parsers/show_commands.py
 A Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-ACL-001.yaml
 A Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-AUTH-002.yaml
 A Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-DOC-001.yaml
 A Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-OSPF-001.yaml
 A Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-SNMP-001.yaml
 A Proyecto-Titulo-Cisco-IOS/src/ios_auditor/rules/evaluation2.py
 M Proyecto-Titulo-Cisco-IOS/src/ios_auditor/rules/registry.py
 M Proyecto-Titulo-Cisco-IOS/src/ios_auditor/services/evidence_batch.py
 M Proyecto-Titulo-Cisco-IOS/src/ios_auditor/services/full_device_analysis.py
 M Proyecto-Titulo-Cisco-IOS/tests/integration/test_api.py
 M Proyecto-Titulo-Cisco-IOS/tests/integration/test_full_device_api.py
 M Proyecto-Titulo-Cisco-IOS/tests/integration/test_samples_and_cli.py
 A Proyecto-Titulo-Cisco-IOS/tests/unit/test_evaluacion_2_validation.py
 A Proyecto-Titulo-Cisco-IOS/tests/unit/test_evaluation2_rules.py
 M Proyecto-Titulo-Cisco-IOS/tests/unit/test_evidence_batch.py
 M Proyecto-Titulo-Cisco-IOS/tests/unit/test_findings.py
 M Proyecto-Titulo-Cisco-IOS/tests/unit/test_full_device_analysis_service.py
 M Proyecto-Titulo-Cisco-IOS/tests/unit/test_full_device_ssh_analysis.py
 M Proyecto-Titulo-Cisco-IOS/tests/unit/test_netmiko_collector.py
 M Proyecto-Titulo-Cisco-IOS/tests/unit/test_rule_registry.py
 M Proyecto-Titulo-Cisco-IOS/tests/unit/test_show_command_parser.py
 M Proyecto-Titulo-Cisco-IOS/tests/unit/test_ssh_analysis.py
?? Proyecto-Titulo-Cisco-IOS/docs/auditoria-migracion-evidencias-evaluacion-2.md
?? Proyecto-Titulo-Cisco-IOS/docs/registro-controles-adicionales-evaluacion-2.md
?? Proyecto-Titulo-Cisco-IOS/docs/registro-expansion-operacional-evaluacion-2.md
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/README.md
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/inseguro/show_access_lists.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/inseguro/show_interfaces.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/inseguro/show_ip_interface_brief.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/inseguro/show_ip_ospf_neighbor.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/inseguro/show_ntp_associations.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/no_evaluable/show_access_lists.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/no_evaluable/show_interfaces.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/no_evaluable/show_ip_interface_brief.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/no_evaluable/show_ip_ospf_neighbor.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/no_evaluable/show_ntp_associations.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/seguro/show_access_lists.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/seguro/show_interfaces.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/seguro/show_ip_interface_brief.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/seguro/show_ip_ospf_neighbor.txt
?? Proyecto-Titulo-Cisco-IOS/samples/evaluacion_2/operacional/seguro/show_ntp_associations.txt
?? Proyecto-Titulo-Cisco-IOS/scripts/evaluacion_2/offline_integral.py
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/domain/operational_sources.py
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/parsers/operational_show.py
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-ACL-002.yaml
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-ADM-003.yaml
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-AUTH-003.yaml
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-AVL-001.yaml
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-INT-001.yaml
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-INT-002.yaml
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-NTP-002.yaml
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/rules/IOS-OSPF-002.yaml
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/textfsm/cisco_ios_show_access_lists.textfsm
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/textfsm/cisco_ios_show_interfaces.textfsm
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/textfsm/cisco_ios_show_ip_ospf_neighbor.textfsm
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/resources/textfsm/cisco_ios_show_ntp_associations.textfsm
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/rules/evaluation2_additional.py
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/rules/evaluation2_operational.py
?? Proyecto-Titulo-Cisco-IOS/src/ios_auditor/rules/interface_unused.py
?? Proyecto-Titulo-Cisco-IOS/tests/unit/test_evaluation2_additional.py
?? Proyecto-Titulo-Cisco-IOS/tests/unit/test_evidence_migration_audit.py
?? Proyecto-Titulo-Cisco-IOS/tests/unit/test_operational_expansion.py
~~~
