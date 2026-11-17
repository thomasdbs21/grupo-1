# Automatización

| Evidencia original | Qué demuestra | Cómo se obtuvo | Fase |
|---|---|---|---|
| [src/ios_auditor/collectors/netmiko_collector.py](../../../../Proyecto-Titulo-Cisco-IOS/src/ios_auditor/collectors/netmiko_collector.py) | Recolección SSH controlada por comandos autorizados | Código original del colector; no ejecutar sin autorización del laboratorio | Fase 2 |
| [src/ios_auditor/parsers/running_config.py](../../../../Proyecto-Titulo-Cisco-IOS/src/ios_auditor/parsers/running_config.py) | Normalización de running-config con CiscoConfParse | Parser original | Fase 2 |
| [src/ios_auditor/parsers/operational_show.py](../../../../Proyecto-Titulo-Cisco-IOS/src/ios_auditor/parsers/operational_show.py) | Interpretación de evidencia operacional con TextFSM | Parser original y plantillas propias | Fase 2 |
| [src/ios_auditor/services/analyzer.py](../../../../Proyecto-Titulo-Cisco-IOS/src/ios_auditor/services/analyzer.py) | Orquestación del análisis determinista | Función analyze_context y uso del registro de reglas | Fase 2; ampliada en Fase 3 |
| [src/ios_auditor/services/rule_results.py](../../../../Proyecto-Titulo-Cisco-IOS/src/ios_auditor/services/rule_results.py) | Derivación de Findings exclusivamente desde FAIL | Código original; sin modificaciones en este encargo | Fases 2 y 3 |

El índice referencia la fuente original; no replica configuraciones completas reales, credenciales ni todo el código. No se inventan salidas ni se ejecutan nuevas sesiones SSH.
