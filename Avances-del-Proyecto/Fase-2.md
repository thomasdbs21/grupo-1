# Fase 2

**Estado:** En desarrollo

## Presentación de avance real del proyecto

**Fecha:** 22 de septiembre de 2026

Durante la sesión se presentó «NetAudit — Avance real del Proyecto de Título», contrastando las capacidades implementadas y las evidencias disponibles con las actividades de la Carta Gantt definida en Fase 1. La presentación se registra como evidencia académica grupal de Fase 2; no constituye el cierre de la fase ni acredita una nueva ejecución de pruebas en la fecha de exposición.

### Avance frente a la Carta Gantt

| Actividad | Estado del alcance presentado | Evidencia y trabajo pendiente |
|---|---|---|
| Alcance y requerimientos | Completado | Problema, objetivos, alcance y restricciones definidos. |
| Arquitectura y laboratorio | Completado para el alcance actual | Arquitectura del auditor y laboratorio CSR1000v con Cisco IOS XE 16.9.5 sobre VirtualBox. |
| Recolección y parsing | Completado para el alcance actual | SSH de solo lectura mediante Netmiko, CiscoConfParse y TextFSM. |
| Motor y catálogo de reglas | En desarrollo | Siete reglas de `running-config` más `IOS-IF-001` operacional; continúa pendiente ampliar la cobertura del catálogo. |
| Integración API/resultados | Completado para el alcance actual | Integración mediante FastAPI y respuesta estructurada y sanitizada. |
| Interfaz y reportes | Pendiente | Componentes posteriores, sin implementación presentada. |
| Pruebas y validación | En desarrollo | Suite automatizada y validación real controlada documentadas; la validación final del proyecto continúa pendiente. |
| Cierre y documentación | En desarrollo | Informes técnicos y presentación de avance disponibles; cierre académico final pendiente. |

### Recolección, procesamiento y motor determinista

La arquitectura separa recopilación, evidencia, parsing, contextos, reglas y presentación de resultados. Netmiko utiliza SSH de solo lectura y una lista blanca de cuatro comandos canónicos:

1. `show running-config`
2. `show version`
3. `show ip interface brief`
4. `show ip ssh`

CiscoConfParse procesa `running-config` y TextFSM estructura las salidas operacionales. El análisis integral aplica siete reglas de configuración y la regla operacional `IOS-IF-001`, conserva todas las evaluaciones y genera findings únicamente desde resultados `FAIL`. FastAPI expone los resultados mediante un contrato tipado y sanitizado.

### Pruebas automatizadas reproducibles

La presentación muestra **314 pruebas automatizadas aprobadas**, con **0 fallos, 0 skipped y 0 warnings**, correspondientes a los resultados del Incremento 8 documentados al 30 de julio de 2026. La suite utilizó simulaciones, datos sintéticos y dobles de prueba: **no abrió sesiones SSH ni ejecutó las 314 pruebas contra el router real**.

### Validación real controlada sobre CSR1000v

De forma independiente de la suite automatizada, se documentó una validación sobre una CSR1000v autorizada con Cisco IOS XE 16.9.5 en VirtualBox. Se utilizó una sesión SSH, los cuatro comandos canónicos y una desconexión, con cuatro evidencias recolectadas y ocho evaluaciones:

| Estado | Cantidad |
|---|---:|
| `PASS` | 4 |
| `FAIL` | 2 |
| `NOT_APPLICABLE` | 1 |
| `NOT_EVALUATED` | 1 |
| `ERROR` | 0 |

Los dos resultados `FAIL` generaron exactamente dos findings de severidad **MEDIUM**: `IOS-NTP-001` e `IOS-LOG-001`. Esta validación demuestra el flujo de solo lectura en el escenario documentado; no equivale a una validación completa de todas las plataformas o condiciones de red.

### Siguiente etapa y actividades pendientes

La persistencia relacional con **PostgreSQL, SQLAlchemy y Alembic** se identificó como siguiente etapa, antes de interfaz y reportes, para conservar análisis históricos de forma estructurada. En el repositorio está definida y planificada como Incremento 9, **sin implementación**.

La interfaz, los reportes y el asistente conversacional de IA permanecen como etapas posteriores. La IA se mantiene como componente complementario para explicar hallazgos determinados por las reglas. La ampliación del catálogo, la validación final y el cierre documental continúan pendientes, por lo que la Fase 2 permanece **En desarrollo**.

### Evidencia académica

[Presentación de avance del 22 de septiembre de 2026](../Entregables-APT/Fase-2/Grupales/Grupo-1_Presentacion_Avance_Proyecto_Fase-2_22-09-2026.pdf)

### Fuentes de contraste

- [Definición del proyecto y Carta Gantt de Fase 1, páginas 5–6](../Entregables-APT/Fase-1/Grupales/Grupo-1_Definicion_Proyecto_APT_Fase-1.pdf).
- [Registro técnico del Incremento 8: pruebas automatizadas y validación real](../Proyecto-Titulo-Cisco-IOS/docs/registro-incremento-8-expansion-reglas-deterministas.md).
- [Definición del Incremento 9: persistencia planificada, no implementada](../Proyecto-Titulo-Cisco-IOS/docs/definicion-incremento-9-persistencia-relacional.md).

## Seguimiento al 12 de octubre de 2026

La [presentación de Evaluación 2 del 6 de octubre](../Entregables-APT/Fase-2/Grupales/NetAudit_Evaluacion_2_APT_06-10-2026.pptx) fue realizada como Evaluación 2 y mostró la ampliación disponible en [feature/evaluacion-2-validacion](https://github.com/thomasdbs21/grupo-1/tree/feature/evaluacion-2-validacion), commit `d3d05ca`: 21 reglas de auditoría, ocho comandos y una campaña sintética histórica de 63/63 coincidencias. La suite de esa rama se ejecutó nuevamente y obtuvo `703 passed, 1 warning in 9.67s`. La campaña y la validación manual real mostradas en la presentación son evidencias históricas; no se repitió SSH en esta preparación.

La ampliación no está fusionada en `main`, que conserva ocho reglas de auditoría y cuatro comandos. Su suite actual obtuvo `314 passed, 1 warning in 7.77s`. Persistencia, interfaz, reportes e IA explicativa continúan pendientes. Las cifras de la presentación no deben atribuirse al código de main. El [PDF de la presentación del 06/10](../Entregables-APT/Fase-2/Grupales/NetAudit_Evaluacion_2_APT_06-10-2026.pdf) facilita su revisión.

La retroalimentación docente solicitó diferenciar mejor el auditor de las herramientas orientadas a aplicar configuraciones. El equipo refuerza el alcance de solo lectura, la trazabilidad de la evidencia y el motor determinista como núcleo. Esta precisión mantiene el objetivo general y la metodología incremental declarados en Fase 1.

| Entregable | Autoría |
|---|---|
| [Diario de Reflexión Fase 2](../Entregables-APT/Fase-2/Grupales/2.1_APT122_DiarioReflexionFase2.docx) | Equipo completo |
| [Guía de Desarrollo APT](../Entregables-APT/Fase-2/Grupales/2.4_GuiaEstudiante_Fase2_DesarrolloProyecto_APT.docx) | Equipo completo |
| [Autoevaluación de Axl Urrutia](../Entregables-APT/Fase-2/Individuales/Axl-Urrutia/2.2_APT122_AutoevaluacionAvance_Fase2_Axl_Urrutia.docx) | Individual; los otros integrantes completan la propia |
| [Especificaciones de presentación futura](../Entregables-APT/Fase-2/Referencias/Especificaciones_Presentacion_Avance_Fase2.docx) | Referencia docente sin modificaciones |

Los originales de los tres instrumentos se conservan en [Plantillas](../Entregables-APT/Fase-2/Referencias/Plantillas/). El [registro de auditoría](Auditoria-2026-10-13.md) contiene el contraste de versiones, las evidencias y las validaciones actuales.

[Volver al índice de avances](README.md)
