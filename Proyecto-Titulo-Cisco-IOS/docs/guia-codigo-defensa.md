# Defensa técnica de NetAudit

## Preparación en VS Code

Abre la carpeta del proyecto técnico. Usa Ctrl+P para abrir una ruta y Ctrl+G para ir a la línea indicada. La página se sirve con `python -m streamlit run apps/streamlit/app.py` en 8501. Uvicorn carga `ios_auditor.api.app:app` en 8000. En el entorno de demostración, los BAT y el lanzador Python son utilidades locales externas al repositorio. Inician los procesos, cargan la configuración privada y comprueban sus servicios. Localhost designa este mismo equipo desde el proceso que hace la petición. El navegador remoto entra a la UI por Radmin; Streamlit accede al backend en localhost y solo FastAPI usa el gateway local de IA en 20128.

## Recorrido para proyectar

Para archivo: carga → FastAPI → contexto normalizado → reglas → evaluaciones → Findings → vista de resultados. El lote de dispositivo añade Netmiko, identificación de ejecución, verificación de evidencias y parsing TextFSM. La explicación comienza después de crear los Findings y llega a la UI a través de FastAPI.

| Archivo y línea | Función | Fragmento real | Frase para la comisión |
|---|---|---|---|
| [apps/streamlit/app.py:180](../apps/streamlit/app.py#L180) | `main` | `client = BackendClient()` | Streamlit ejecuta main() al cargar el archivo; aquí se crea BackendClient y se dibuja la interfaz. |
| [src/ios_auditor/ui/backend.py:46](../src/ios_auditor/ui/backend.py#L46) | `BackendClient.analyze_file` | `return self._request("POST", "/api/v1/analyses", files={"file": (filename, content, "application/octet-stream")})` | El botón de análisis sube el archivo al backend por HTTP y devuelve el resultado de esa ejecución. |
| [src/ios_auditor/api/app.py:315](../src/ios_auditor/api/app.py#L315) | `create_analysis` | `result = analyze_bytes(raw, source_name=source_name, registry=registry)` | FastAPI lee el archivo y llama al servicio de análisis. Conserva el resultado antes de registrar el contexto opcional de IA. |
| [src/ios_auditor/services/analyzer.py:123](../src/ios_auditor/services/analyzer.py#L123) | `analyze_context` | `findings = findings_from_evaluations(evaluations)` | La misma entrada alimenta todas las reglas habilitadas del registro en el mismo orden. |
| [src/ios_auditor/rules/explicit_services.py:35](../src/ios_auditor/rules/explicit_services.py#L35) | `ExplicitDirectiveRule.evaluate` | `states.setdefault(RuleStatus.PASS if negated else RuleStatus.FAIL, block.head.number)` | La regla distingue directiva positiva, negación y falta de evidencia. Conserva la línea para que podamos defender el hallazgo. |
| [src/ios_auditor/services/rule_results.py:24](../src/ios_auditor/services/rule_results.py#L24) | `findings_from_evaluations` | `if evaluation.status is RuleStatus.FAIL` | Un hallazgo copia severidad y evidencia de una evaluación fallida. PASS y los estados indeterminados quedan en el informe. |
| [src/ios_auditor/services/ssh_analysis.py:152](../src/ios_auditor/services/ssh_analysis.py#L152) | `collect_and_analyze_device` | `validated_batch = validate_evidence_batch(evidences)` | Si el origen es un equipo, agrupamos las ocho consultas de lectura en una ejecución. |
| [src/ios_auditor/collectors/netmiko_collector.py:99](../src/ios_auditor/collectors/netmiko_collector.py#L99) | `NetmikoCollector.collect` | `normalized_commands = self._validate_commands(commands)` | Validamos las consultas antes de conectar y cerramos la sesión en finally. |
| [src/ios_auditor/parsers/running_config.py:25](../src/ios_auditor/parsers/running_config.py#L25) | `parse_running_config` | `parse = CiscoConfParse(list(raw_lines), syntax="ios")` | CiscoConfParse interpreta la jerarquía IOS; conservamos referencias a las líneas originales. |
| [src/ios_auditor/parsers/show_commands.py:73](../src/ios_auditor/parsers/show_commands.py#L73) | `_parse_rows` | `template = textfsm.TextFSM(template_stream)` | TextFSM aplica la plantilla del comando para extraer filas de datos operacionales. |
| [src/ios_auditor/services/full_device_analysis.py:53](../src/ios_auditor/services/full_device_analysis.py#L53) | `analyze_validated_evidence_batch` | `configuration_result = analyze_bytes(` | La configuración y las observaciones operacionales se evalúan dentro del mismo lote validado. |
| [src/ios_auditor/api/ai_routes.py:31](../src/ios_auditor/api/ai_routes.py#L31) | `explain_analysis` | `context = repository.get(analysis_id)` | El ID recupera el contexto que creó el backend para el análisis. |
| [src/ios_auditor/ai/service.py:35](../src/ios_auditor/ai/service.py#L35) | `build_context` | `safe = FindingContext(` | Solo se incluyen Findings deterministas, con texto sanitizado y evidencia limitada. |
| [src/ios_auditor/ai/prompts.py:30](../src/ios_auditor/ai/prompts.py#L30) | `build_messages` | `"findings": [item.model_dump(mode="json") for item in context.findings],` | Los hallazgos y la pregunta se transmiten como datos no confiables junto con el esquema de salida. |
| [src/ios_auditor/ai/client.py:63](../src/ios_auditor/ai/client.py#L63) | `OmniRouteClient._complete_once` | `with client.stream("POST", self.settings.base_url + "/chat/completions",` | El cliente HTTP solicita la explicación al gateway con el modelo configurado. |
| [src/ios_auditor/ai/service.py:78](../src/ios_auditor/ai/service.py#L78) | `ExplanationService.explain` | `explanation = Explanation.model_validate_json(raw)` | Pydantic valida la estructura. La comprobación posterior exige exactamente los ID presentes en el contexto. |
| [apps/streamlit/app.py:61](../apps/streamlit/app.py#L61) | `show_explanation` | `st.write(explanation['summary'])` | Streamlit presenta el resumen, impacto y revisión manual devueltos por la API. |
| [src/ios_auditor/ui/presentation.py:71](../src/ios_auditor/ui/presentation.py#L71) | `csv_export` | `def csv_export(analysis: dict) -> bytes:` | La exportación parte del análisis y genera datos para compartir o revisar. |

## Preguntas para ensayar

1. **¿Dónde se levanta la web?** Streamlit ejecuta el archivo de la aplicación y llama a main. El servidor y la interfaz se ejecutan en el anfitrión.
2. **¿Qué es Streamlit?** Es la biblioteca que construye el formulario, mantiene la sesión y muestra los resultados en el navegador.
3. **¿Para qué sirve FastAPI?** Define y valida las solicitudes de archivo, dispositivo, consulta y explicación, y llama a los servicios del dominio.
4. **¿Por qué HTTP?** La UI y el backend son procesos distintos. El contrato HTTP permite probar la API con un cliente de pruebas sin desplegar la interfaz.
5. **¿Dónde entra Netmiko?** El collector recibe la fábrica de conexiones. En producción crea una conexión Cisco IOS y usa send_command para cada consulta autorizada.
6. **¿Qué es running-config?** La configuración activa del equipo. El modo archivo puede analizar una copia sin acceder al dispositivo.
7. **¿En qué se diferencian los parsers?** CiscoConfParse permite recorrer directivas y secciones de configuración. TextFSM extrae columnas de salidas operacionales según el comando.
8. **¿Cómo decide una regla?** Compara evidencia concreta con un criterio fijo. Por ejemplo, la nueva regla de Finger requiere una directiva global explícita y coherente.
9. **¿Evaluación o hallazgo?** Cada regla habilitada produce una RuleEvaluation. Solo FAIL produce un Finding.
10. **¿Quién asigna la severidad?** Se define en los metadatos de la regla y se copia al hallazgo.
11. **¿Qué evidencia se conserva?** El resultado vincula fuente, hash, fragmento y línea cuando existe. En el lote de dispositivo también hay UUID, comando y hora de adquisición.
12. **¿Qué ocurre si falta información?** Una regla aplicable puede quedar NOT_EVALUATED. NOT_APPLICABLE expresa que no corresponde al caso. Un lote que viola su contrato se rechaza antes de combinar evidencias.
13. **¿Cómo se llama a Gemini?** El backend construye mensajes con contexto sanitizado y llama por HTTP a OmniRoute, que enruta al proveedor configurado.
14. **¿Qué aporta el gateway?** Separa el modelo y su autenticación del cliente web. Su endpoint de salud acredita accesibilidad; la inferencia requiere una prueba distinta.
15. **¿Qué pasa con un 503?** La vista muestra el error de explicación. Según el origen y los plazos puede llegar como fallo upstream o timeout. Los resultados deterministas ya están disponibles.
16. **¿Puede la IA modificar un resultado?** El servicio recibe una copia limitada, sin herramientas de red. Valida un esquema de explicación y comprueba los identificadores contra los Findings existentes.
17. **¿Cómo se mantiene solo lectura?** Se valida la lista blanca antes de abrir SSH. El collector envía consultas show y cierra la sesión, incluso si una consulta falla.
18. **¿Cómo se comprueban las reglas?** Con entradas positivas, negativas, ambiguas y pruebas de integración. La campaña offline compara resultados con expectativas independientes.
19. **¿Cuál fue la validación real?** El registro histórico del laboratorio conserva su propio alcance. Las nuevas reglas se comprobaron con archivos y lotes sintéticos. La campaña actual no abrió SSH.
20. **¿Cuáles son los límites?** Se admite un subconjunto de sintaxis y plataformas. La ausencia de estas directivas no permite inferir un valor efectivo. La explicación depende de la disponibilidad del proveedor.

## Distribución del estudio

Axl explica arquitectura, registro y contratos. Thomas opera la demo y explica el ciclo de adquisición SSH. Maikol justifica las decisiones y las pruebas de falsos positivos. Emilio conduce la lectura de la interfaz, evidencia y exportaciones. Cada integrante ensaya también el recorrido completo desde el archivo hasta un Finding.

## Revisión de comentarios del 9 de noviembre

Se revisaron los 93 archivos Python propios. Se ampliaron 74 archivos con comentarios de responsabilidad, clases, contratos y bloques de decisión. Los 19 restantes ya tienen documentación adecuada a su tamaño y función. La comparación con HEAD conserva íntegros el AST y los tokens ejecutables en los 93 archivos. El cambio añade comentarios; las docstrings existentes se conservan. El proyecto no versiona BAT ni PowerShell propios en este corte.

| Archivo revisado | Resultado de la revisión |
|---|---|
| [apps/streamlit/app.py](../apps/streamlit/app.py) | Comentarios ampliados en esta revisión. |
| [scripts/evaluacion_2/offline_integral.py](../scripts/evaluacion_2/offline_integral.py) | Comentarios ampliados en esta revisión. |
| [scripts/evaluacion_2/run_csr1000v_validation.py](../scripts/evaluacion_2/run_csr1000v_validation.py) | Comentarios ampliados en esta revisión. |
| [scripts/evaluacion_2/run_validation_scenarios.py](../scripts/evaluacion_2/run_validation_scenarios.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/__init__.py](../src/ios_auditor/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/__main__.py](../src/ios_auditor/__main__.py) | Entrada de cinco líneas que delega en cli.main. |
| [src/ios_auditor/ai/__init__.py](../src/ios_auditor/ai/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/ai/client.py](../src/ios_auditor/ai/client.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/ai/contracts.py](../src/ios_auditor/ai/contracts.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/ai/errors.py](../src/ios_auditor/ai/errors.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/ai/prompts.py](../src/ios_auditor/ai/prompts.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/ai/repository.py](../src/ios_auditor/ai/repository.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/ai/sanitization.py](../src/ios_auditor/ai/sanitization.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/ai/service.py](../src/ios_auditor/ai/service.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/ai/settings.py](../src/ios_auditor/ai/settings.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/api/__init__.py](../src/ios_auditor/api/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/api/ai_routes.py](../src/ios_auditor/api/ai_routes.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/api/app.py](../src/ios_auditor/api/app.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/api/dependencies.py](../src/ios_auditor/api/dependencies.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/api/errors.py](../src/ios_auditor/api/errors.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/api/full_device_serialization.py](../src/ios_auditor/api/full_device_serialization.py) | Docstrings existentes describen el contrato público y sus exclusiones. |
| [src/ios_auditor/api/repository.py](../src/ios_auditor/api/repository.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/api/schemas.py](../src/ios_auditor/api/schemas.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/cli.py](../src/ios_auditor/cli.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/collectors/__init__.py](../src/ios_auditor/collectors/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/collectors/netmiko_collector.py](../src/ios_auditor/collectors/netmiko_collector.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/domain/__init__.py](../src/ios_auditor/domain/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/domain/full_device.py](../src/ios_auditor/domain/full_device.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/domain/models.py](../src/ios_auditor/domain/models.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/domain/operational_sources.py](../src/ios_auditor/domain/operational_sources.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/parsers/__init__.py](../src/ios_auditor/parsers/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/parsers/operational_show.py](../src/ios_auditor/parsers/operational_show.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/parsers/running_config.py](../src/ios_auditor/parsers/running_config.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/parsers/show_commands.py](../src/ios_auditor/parsers/show_commands.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/resources/__init__.py](../src/ios_auditor/resources/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/resources/rules/__init__.py](../src/ios_auditor/resources/rules/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/resources/textfsm/__init__.py](../src/ios_auditor/resources/textfsm/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/rules/__init__.py](../src/ios_auditor/rules/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/rules/base.py](../src/ios_auditor/rules/base.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/evaluation2.py](../src/ios_auditor/rules/evaluation2.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/evaluation2_additional.py](../src/ios_auditor/rules/evaluation2_additional.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/evaluation2_operational.py](../src/ios_auditor/rules/evaluation2_operational.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/explicit_services.py](../src/ios_auditor/rules/explicit_services.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/increment8.py](../src/ios_auditor/rules/increment8.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/interface_unused.py](../src/ios_auditor/rules/interface_unused.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/metadata.py](../src/ios_auditor/rules/metadata.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/operational.py](../src/ios_auditor/rules/operational.py) | Clase y fábrica documentadas; ramas PASS, FAIL y estados no binarios con mensajes explícitos. |
| [src/ios_auditor/rules/pilot.py](../src/ios_auditor/rules/pilot.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/rules/registry.py](../src/ios_auditor/rules/registry.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/services/__init__.py](../src/ios_auditor/services/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/services/analyzer.py](../src/ios_auditor/services/analyzer.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/services/evidence_batch.py](../src/ios_auditor/services/evidence_batch.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/services/full_device_analysis.py](../src/ios_auditor/services/full_device_analysis.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/services/operational_analysis.py](../src/ios_auditor/services/operational_analysis.py) | Docstrings existentes explican parsing, contratos y errores de evidencia. |
| [src/ios_auditor/services/rule_results.py](../src/ios_auditor/services/rule_results.py) | Función corta con docstring y comentario que explican la derivación exclusiva desde FAIL. |
| [src/ios_auditor/services/serialization.py](../src/ios_auditor/services/serialization.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/services/ssh_analysis.py](../src/ios_auditor/services/ssh_analysis.py) | Orquestadores y contratos documentados; el comentario previo ubica la frontera entre adquisición y evaluación. |
| [src/ios_auditor/ui/__init__.py](../src/ios_auditor/ui/__init__.py) | Marcador de paquete o reexportaciones breves con nombres explícitos; no incorpora lógica de decisión. |
| [src/ios_auditor/ui/backend.py](../src/ios_auditor/ui/backend.py) | Comentarios ampliados en esta revisión. |
| [src/ios_auditor/ui/presentation.py](../src/ios_auditor/ui/presentation.py) | Comentarios ampliados en esta revisión. |
| [tests/integration/test_ai_api.py](../tests/integration/test_ai_api.py) | Comentarios ampliados en esta revisión. |
| [tests/integration/test_api.py](../tests/integration/test_api.py) | Comentarios ampliados en esta revisión. |
| [tests/integration/test_full_device_api.py](../tests/integration/test_full_device_api.py) | Comentarios ampliados en esta revisión. |
| [tests/integration/test_samples_and_cli.py](../tests/integration/test_samples_and_cli.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_ai_client_service.py](../tests/unit/test_ai_client_service.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_ai_sanitization.py](../tests/unit/test_ai_sanitization.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_api_repository.py](../tests/unit/test_api_repository.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_evaluacion_2_validation.py](../tests/unit/test_evaluacion_2_validation.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_evaluation2_additional.py](../tests/unit/test_evaluation2_additional.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_evaluation2_rules.py](../tests/unit/test_evaluation2_rules.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_evidence_batch.py](../tests/unit/test_evidence_batch.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_evidence_migration_audit.py](../tests/unit/test_evidence_migration_audit.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_explicit_services.py](../tests/unit/test_explicit_services.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_findings.py](../tests/unit/test_findings.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_full_device_analysis_result.py](../tests/unit/test_full_device_analysis_result.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_full_device_analysis_service.py](../tests/unit/test_full_device_analysis_service.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_full_device_api_contracts.py](../tests/unit/test_full_device_api_contracts.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_full_device_ssh_analysis.py](../tests/unit/test_full_device_ssh_analysis.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_in_memory_analysis.py](../tests/unit/test_in_memory_analysis.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_increment8_rules.py](../tests/unit/test_increment8_rules.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_loader_and_parser.py](../tests/unit/test_loader_and_parser.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_netmiko_collector.py](../tests/unit/test_netmiko_collector.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_operational_analysis.py](../tests/unit/test_operational_analysis.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_operational_expansion.py](../tests/unit/test_operational_expansion.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_operational_rule.py](../tests/unit/test_operational_rule.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_rule_metadata.py](../tests/unit/test_rule_metadata.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_rule_registry.py](../tests/unit/test_rule_registry.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_rules.py](../tests/unit/test_rules.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_show_command_parser.py](../tests/unit/test_show_command_parser.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_ssh_analysis.py](../tests/unit/test_ssh_analysis.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_streamlit_mvp.py](../tests/unit/test_streamlit_mvp.py) | Comentarios ampliados en esta revisión. |
| [tests/unit/test_ui_ux_refinement.py](../tests/unit/test_ui_ux_refinement.py) | Comentarios ampliados en esta revisión. |
| [tests_live/test_ai_live.py](../tests_live/test_ai_live.py) | Prueba optativa ya documentada y condicionada por configuración explícita. |
