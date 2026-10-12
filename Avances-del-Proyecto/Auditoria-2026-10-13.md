# Preparación de auditoría académica del 13 de octubre de 2026

Revisión efectuada el 12/10/2026 sobre el repositorio `thomasdbs21/grupo-1`. Los documentos académicos describen el alcance verificado y distinguen las dos versiones técnicas disponibles.

## Evidencias y entregables

| Requisito | Evidencia localizada | Estado y acción |
|---|---|---|
| Definición, alcance, objetivos y metodología | [Definición de Fase 1](../Entregables-APT/Fase-1/Grupales/Grupo-1_Definicion_Proyecto_APT_Fase-1.pdf) | Presente; metodología incremental, página 4 |
| Carta Gantt | Mismo documento, páginas 5–6 | Presente; ocho actividades, S1–S18; sin fecha inicial que permita calendarizar retrasos |
| Documentos individuales de Fase 1 | [Individuales](../Entregables-APT/Fase-1/Individuales/) | Autoevaluación y reflexión de los cuatro integrantes |
| Presentación de Fase 1 | [Presentación inicial](../Entregables-APT/Fase-1/Grupales/Grupo-1_Presentacion_Proyecto_Fase-1.pptx) | Presente |
| Presentación del 22/09/2026 | [PDF de avance](../Entregables-APT/Fase-2/Grupales/Grupo-1_Presentacion_Avance_Proyecto_Fase-2_22-09-2026.pdf) | Presente |
| Presentación del 06/10/2026 | [PPTX de Evaluación 2](../Entregables-APT/Fase-2/Grupales/NetAudit_Evaluacion_2_APT_06-10-2026.pptx) | Presentación realizada como Evaluación 2; PPTX y [PDF](../Entregables-APT/Fase-2/Grupales/NetAudit_Evaluacion_2_APT_06-10-2026.pdf) |
| Diario grupal | [2.1](../Entregables-APT/Fase-2/Grupales/2.1_APT122_DiarioReflexionFase2.docx) | Seis preguntas originales y respuestas del equipo |
| Autoevaluación | [2.2 de Axl](../Entregables-APT/Fase-2/Individuales/Axl-Urrutia/2.2_APT122_AutoevaluacionAvance_Fase2_Axl_Urrutia.docx) | Solo Axl; rúbrica original conservada |
| Guía de desarrollo | [2.4](../Entregables-APT/Fase-2/Grupales/2.4_GuiaEstudiante_Fase2_DesarrolloProyecto_APT.docx) | Avance, ocho filas de actividades con responsables completos, factores, ajustes y pendientes |
| Originales docentes | [Plantillas](../Entregables-APT/Fase-2/Referencias/Plantillas/) y [especificaciones](../Entregables-APT/Fase-2/Referencias/Especificaciones_Presentacion_Avance_Fase2.docx) | Copias sin modificación de contenido |

Se conserva el PPTX de tres diapositivas y una exportación PDF del mismo archivo. Las versiones y guiones locales alternativos se preservan fuera de esta entrega.

## Estado técnico por versión

| Componente | main (base c78570f) | Rama Evaluación 2 (d3d05ca) |
|---|---|---|
| Reglas de auditoría | 8: 7 de configuración y 1 operacional | 21: 14 de configuración y 7 operacionales |
| Recolección integral | 4 comandos y 4 evidencias | 8 comandos y 8 evidencias |
| Parsing operacional | 3 contextos TextFSM | 7 contextos TextFSM |
| CLI y API FastAPI | Implementados y cubiertos por pruebas | Implementados y cubiertos por pruebas |
| PostgreSQL / SQLAlchemy / Alembic | Planificados, no implementados | Sin implementación |
| Interfaz final, reportes e IA | Pendientes | Pendientes |

La ampliación sigue en [feature/evaluacion-2-validacion](https://github.com/thomasdbs21/grupo-1/tree/feature/evaluacion-2-validacion); no se fusiona código funcional mediante el PR documental. Sus [registros actuales](https://github.com/thomasdbs21/grupo-1/blob/feature/evaluacion-2-validacion/Proyecto-Titulo-Cisco-IOS/docs/registro-controles-adicionales-evaluacion-2.md) detallan la campaña sintética y la validación manual reportada. La evidencia de laboratorio no demuestra cobertura universal de Cisco IOS/IOS XE.

El recolector usa una lista blanca y `send_command()`; no aplica configuración. Las reglas reciben contextos inmutables. Se conservan todos los estados y solo `FAIL` origina findings. La IA explicativa futura no decide cumplimiento ni modifica evidencia, severidad o dispositivos.

## Validaciones ejecutadas

Con el entorno `.venv` existente y `PYTHONUTF8=1`, sobre copias exactas obtenidas con `git archive` de main (`c78570f`) y de la rama adicional (`d3d05ca`), sin instalar dependencias ni abrir sesiones SSH:

| Revisión | Resultado exacto |
|---|---|
| Rama Evaluación 2, `python -m pytest -q` | `703 passed, 1 warning in 9.67s` |
| main, `python -m pytest -q` | `314 passed, 1 warning in 7.77s` |

Ambas suites terminaron sin fallos ni skipped. El warning es `DeprecationWarning` de Starlette por el alias `anyio.abc.BlockingPortal`; no se ocultó ni se trató como fallo.

Los resultados históricos de 63/63 escenarios y de una sesión CSR1000v con 21 evaluaciones y tres findings están documentados en la rama ampliada. No se repitieron como validaciones reales durante esta preparación.

## Preparación de la muestra

Abrir el README raíz y seguir sus enlaces a Fase 1, Carta Gantt, presentaciones y documentos Fase 2. Al demostrar código, identificar la rama: main tiene ocho reglas de auditoría; la presentación del 6 de octubre corresponde a la rama ampliada de 21. Mantener ocultas las credenciales y datos reales del laboratorio.

Quedan pendientes el informe académico consolidado, los apartados requeridos en inglés y la definición de indicadores disciplinarios con la docente. El proyecto sigue en desarrollo y no se presenta como cerrado.

## Revisión de los instrumentos académicos

La Guía utiliza las competencias oficiales completas 5, 5, 4, 4, 5, 5, 4 y 5 para las ocho actividades, respectivamente. Se conservan las preguntas, logos, tablas y estructura de los tres instrumentos. Los DOCX se revisaron visualmente en sus 16 páginas; también se revisaron las tres diapositivas del PDF de Evaluación 2.

La autoevaluación de Axl conserva ocho marcas: Logrado, Completamente logrado, Logrado, Logrado, Logrado, Logrado, Logrado y No logrado. El Indicador 2 se respalda en la metodología de desarrollo incremental declarada en la Definición de Fase 1, página 4, y su aplicación documentada en `Proyecto-Titulo-Cisco-IOS/docs/plan-incremental.md`, secciones 4 a 11, con código, pruebas y registros de cierre de los incrementos. El Indicador 8 sigue como No logrado porque los apartados académicos requeridos en inglés aún no están disponibles.

Se limpiaron dos coincidencias internas de la presentación: una propiedad del archivo y un término de una nota del expositor. Las diapositivas, imágenes y evidencias visuales permanecen idénticas al archivo recibido.
