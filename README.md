# NetAudit

Repositorio académico grupal del Proyecto de Título de la carrera de Ingeniería en Conectividad y Redes de Duoc UC, sede San Joaquín.

## Equipo

- Axl Urrutia
- Thomas Henriquez
- Maikol Mamani
- Emilio Cortes

## Descripción del proyecto

NetAudit es un asistente orientado al análisis técnico de configuraciones Cisco IOS e IOS XE. El proyecto busca apoyar a administradores de red y equipos de soporte y operación en la detección de configuraciones incorrectas, controles de seguridad ausentes, inconsistencias y malas prácticas.

La solución mantiene un enfoque de solo lectura: recopila información autorizada, la normaliza y la evalúa mediante reglas deterministas. La inteligencia artificial está planificada como componente complementario para explicar resultados y recomendaciones; el cumplimiento técnico lo decide el motor determinista. NetAudit obtiene evidencia y audita condiciones verificables, sin aplicar configuraciones ni reemplazar herramientas de despliegue de cambios.

## Estado actual

Al 12 de octubre de 2026, `main` contiene los Incrementos 0 a 8: ocho reglas deterministas, cuatro comandos SSH y API FastAPI. La revisión actual obtuvo **314 passed, 1 warning**. El warning corresponde a una dependencia y no es un fallo.

La ampliación presentada el 6 de octubre está implementada en la rama [feature/evaluacion-2-validacion](https://github.com/thomasdbs21/grupo-1/tree/feature/evaluacion-2-validacion), commit `d3d05ca`: 21 reglas de auditoría (14 de configuración y 7 operacionales), ocho comandos y **703 passed, 1 warning** en la revisión actual. Esa ampliación **todavía no está fusionada en main**. La presentación se conserva como evidencia de esa versión.

La persistencia relacional con PostgreSQL, SQLAlchemy y Alembic está planificada como Incremento 9. La interfaz final, los reportes y la IA explicativa siguen pendientes. Los resultados de la API de archivos se conservan temporalmente en memoria.

El laboratorio utilizado para las validaciones reales de los Incrementos 4 a 8 fue una CSR1000v con IOS XE 16.9.5 ejecutada en VirtualBox. GNS3 permanece como una alternativa futura sujeta a la disponibilidad legal de imágenes autorizadas.

## Organización del repositorio

~~~text
grupo-1/
├── README.md
├── Avances-del-Proyecto/
│   ├── README.md
│   ├── Fase-1.md
│   ├── Fase-2.md
│   ├── Fase-3.md
│   └── historial-git.md
├── Entregables-APT/
│   ├── Fase-1/
│   │   ├── Individuales/
│   │   └── Grupales/
│   ├── Fase-2/
│   └── Fase-3/
└── Proyecto-Titulo-Cisco-IOS/
~~~

- [`Proyecto-Titulo-Cisco-IOS/`](Proyecto-Titulo-Cisco-IOS/README.md) contiene el código, las pruebas, las muestras y la documentación técnica.
- [`Entregables-APT/`](Entregables-APT/) reúne los documentos académicos, separados por fase, autoría individual y trabajo grupal.
- [`Avances-del-Proyecto/`](Avances-del-Proyecto/README.md) resume el progreso académico y técnico y conserva un historial Git explicado.

## Navegación por fases

- [Fase 1](Avances-del-Proyecto/Fase-1.md): avance documentado y [entregables disponibles](Entregables-APT/Fase-1/).
- [Fase 2](Avances-del-Proyecto/Fase-2.md): presentaciones, reflexión grupal, guía de desarrollo y autoevaluación de Axl.
- [Fase 3](Avances-del-Proyecto/Fase-3.md): estructura preparada, pendiente de evidencia.
- [Historial Git](Avances-del-Proyecto/historial-git.md): explicación cronológica de los commits del proyecto.

## Documentos para la auditoría del 13 de octubre

| Documento | Ubicación |
|---|---|
| Definición, objetivos, metodología y Carta Gantt (páginas 5–6) | [Definición de Fase 1](Entregables-APT/Fase-1/Grupales/Grupo-1_Definicion_Proyecto_APT_Fase-1.pdf) |
| Presentación de Fase 1 | [Presentación inicial](Entregables-APT/Fase-1/Grupales/Grupo-1_Presentacion_Proyecto_Fase-1.pptx) |
| Presentación del 22/09/2026 | [Avance de Fase 2](Entregables-APT/Fase-2/Grupales/Grupo-1_Presentacion_Avance_Proyecto_Fase-2_22-09-2026.pdf) |
| Presentación realizada del 06/10/2026 | [PDF](Entregables-APT/Fase-2/Grupales/NetAudit_Evaluacion_2_APT_06-10-2026.pdf) · [PPTX](Entregables-APT/Fase-2/Grupales/NetAudit_Evaluacion_2_APT_06-10-2026.pptx) |
| Diario de reflexión grupal | [2.1 grupal](Entregables-APT/Fase-2/Grupales/2.1_APT122_DiarioReflexionFase2.docx) |
| Autoevaluación individual | [2.2 de Axl Urrutia](Entregables-APT/Fase-2/Individuales/Axl-Urrutia/2.2_APT122_AutoevaluacionAvance_Fase2_Axl_Urrutia.docx) |
| Guía de desarrollo del proyecto | [2.4 grupal](Entregables-APT/Fase-2/Grupales/2.4_GuiaEstudiante_Fase2_DesarrolloProyecto_APT.docx) |
| Plantillas y especificaciones docentes | [Referencias de Fase 2](Entregables-APT/Fase-2/Referencias/) |
| Verificación del repositorio y resultados actuales | [Registro de auditoría](Avances-del-Proyecto/Auditoria-2026-10-13.md) |

La presentación realizada como Evaluación 2 el 6 de octubre conserva el PPTX entregado por el equipo y una exportación PDF para consulta. Las plantillas oficiales se conservan completas; las copias de trabajo mantienen su diseño. Las especificaciones de presentación se almacenan como referencia futura.

## Desarrollo técnico

La implementación se mantiene en [`Proyecto-Titulo-Cisco-IOS/`](Proyecto-Titulo-Cisco-IOS/README.md). Allí se documentan la arquitectura, las reglas, las decisiones técnicas, el plan incremental y las instrucciones de instalación y uso.

Entre las capacidades implementadas se encuentran:

- análisis local de archivos `running-config`;
- recopilación SSH de solo lectura mediante Netmiko y una lista blanca de cuatro comandos;
- parsing de información operacional mediante TextFSM;
- motor determinista de reglas con evaluaciones y hallazgos trazables;
- API FastAPI para análisis de archivos y dispositivos;
- respuesta sanitizada, sin credenciales ni configuraciones completas.

## Convención de commits

A partir de esta reorganización se mantendrán los prefijos convencionales y se escribirán las descripciones en español.

Ejemplos:

~~~text
feat: agregar persistencia del análisis
fix: corregir sanitización de evidencia
docs: documentar avances de la fase 2
test: agregar pruebas del repositorio relacional
chore: organizar entregables individuales
~~~

Las contribuciones deben conservar la trazabilidad de autoría, evitar datos sensibles y separar los cambios documentales de las modificaciones técnicas. Los commits históricos no se reescriben.
