# Defensa técnica de NetAudit

## Preparación en VS Code

Abre la carpeta del proyecto técnico. Usa Ctrl+P para abrir una ruta y Ctrl+G para ir a la línea indicada. La página se sirve con `python -m streamlit run apps/streamlit/app.py` en 8501. Uvicorn carga `ios_auditor.api.app:app` en 8000. En el entorno de demostración, los BAT y el lanzador Python son utilidades locales externas al repositorio. Inician los procesos, cargan la configuración privada y comprueban sus servicios. Localhost designa este mismo equipo desde el proceso que hace la petición. El navegador remoto entra a la UI por Radmin; Streamlit accede al backend en localhost y solo FastAPI usa el gateway local de IA en 20128.

## Recorrido para proyectar

Para archivo: carga → FastAPI → contexto normalizado → reglas → evaluaciones → Findings → vista de resultados. El lote de dispositivo añade Netmiko, identificación de ejecución, verificación de evidencias y parsing TextFSM. La explicación comienza después de crear los Findings y llega a la UI a través de FastAPI.

| Archivo y línea | Función | Fragmento real | Frase para la comisión |
|---|---|---|---|
| [apps/streamlit/app.py:170](../apps/streamlit/app.py#L170) | `main` | `client = BackendClient()` | Streamlit ejecuta main() al cargar el archivo; aquí se crea BackendClient y se dibuja la interfaz. |
| [src/ios_auditor/ui/backend.py:43](../src/ios_auditor/ui/backend.py#L43) | `BackendClient.analyze_file` | `return self._request("POST", "/api/v1/analyses", files={"file": (filename, content, "application/octet-stream")})` | El botón de análisis sube el archivo al backend por HTTP y devuelve el resultado de esa ejecución. |
| [src/ios_auditor/api/app.py:300](../src/ios_auditor/api/app.py#L300) | `create_analysis` | `result = analyze_bytes(raw, source_name=source_name, registry=registry)` | FastAPI lee el archivo y llama al servicio de análisis. Conserva el resultado antes de registrar el contexto opcional de IA. |
| [src/ios_auditor/services/analyzer.py:117](../src/ios_auditor/services/analyzer.py#L117) | `analyze_context` | `findings = findings_from_evaluations(evaluations)` | La misma entrada alimenta todas las reglas habilitadas del registro en el mismo orden. |
| [src/ios_auditor/rules/explicit_services.py:34](../src/ios_auditor/rules/explicit_services.py#L34) | `ExplicitDirectiveRule.evaluate` | `states.setdefault(RuleStatus.PASS if negated else RuleStatus.FAIL, block.head.number)` | La regla distingue directiva positiva, negación y falta de evidencia. Conserva la línea para que podamos defender el hallazgo. |
| [src/ios_auditor/services/rule_results.py:24](../src/ios_auditor/services/rule_results.py#L24) | `findings_from_evaluations` | `if evaluation.status is RuleStatus.FAIL` | Un hallazgo copia severidad y evidencia de una evaluación fallida. PASS y los estados indeterminados quedan en el informe. |
| [src/ios_auditor/services/ssh_analysis.py:152](../src/ios_auditor/services/ssh_analysis.py#L152) | `collect_and_analyze_device` | `validated_batch = validate_evidence_batch(evidences)` | Si el origen es un equipo, agrupamos las ocho consultas de lectura en una ejecución. |
| [src/ios_auditor/collectors/netmiko_collector.py:99](../src/ios_auditor/collectors/netmiko_collector.py#L99) | `NetmikoCollector.collect` | `normalized_commands = self._validate_commands(commands)` | Validamos las consultas antes de conectar y cerramos la sesión en finally. |
| [src/ios_auditor/parsers/running_config.py:23](../src/ios_auditor/parsers/running_config.py#L23) | `parse_running_config` | `parse = CiscoConfParse(list(raw_lines), syntax="ios")` | CiscoConfParse interpreta la jerarquía IOS; conservamos referencias a las líneas originales. |
| [src/ios_auditor/parsers/show_commands.py:72](../src/ios_auditor/parsers/show_commands.py#L72) | `_parse_rows` | `template = textfsm.TextFSM(template_stream)` | TextFSM aplica la plantilla del comando para extraer filas de datos operacionales. |
| [src/ios_auditor/services/full_device_analysis.py:53](../src/ios_auditor/services/full_device_analysis.py#L53) | `analyze_validated_evidence_batch` | `configuration_result = analyze_bytes(` | La configuración y las observaciones operacionales se evalúan dentro del mismo lote validado. |
| [src/ios_auditor/api/ai_routes.py:29](../src/ios_auditor/api/ai_routes.py#L29) | `explain_analysis` | `context = repository.get(analysis_id)` | El ID recupera el contexto que creó el backend para el análisis. |
| [src/ios_auditor/ai/service.py:34](../src/ios_auditor/ai/service.py#L34) | `build_context` | `safe = FindingContext(` | Solo se incluyen Findings deterministas, con texto sanitizado y evidencia limitada. |
| [src/ios_auditor/ai/prompts.py:29](../src/ios_auditor/ai/prompts.py#L29) | `build_messages` | `"findings": [item.model_dump(mode="json") for item in context.findings],` | Los hallazgos y la pregunta se transmiten como datos no confiables junto con el esquema de salida. |
| [src/ios_auditor/ai/client.py:58](../src/ios_auditor/ai/client.py#L58) | `OmniRouteClient._complete_once` | `with client.stream("POST", self.settings.base_url + "/chat/completions",` | El cliente HTTP solicita la explicación al gateway con el modelo configurado. |
| [src/ios_auditor/ai/service.py:73](../src/ios_auditor/ai/service.py#L73) | `ExplanationService.explain` | `explanation = Explanation.model_validate_json(raw)` | Pydantic valida la estructura. La comprobación posterior exige exactamente los ID presentes en el contexto. |
| [apps/streamlit/app.py:57](../apps/streamlit/app.py#L57) | `show_explanation` | `st.write(explanation['summary'])` | Streamlit presenta el resumen, impacto y revisión manual devueltos por la API. |
| [src/ios_auditor/ui/presentation.py:68](../src/ios_auditor/ui/presentation.py#L68) | `csv_export` | `def csv_export(analysis: dict) -> bytes:` | La exportación parte del análisis y genera datos para compartir o revisar. |

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
