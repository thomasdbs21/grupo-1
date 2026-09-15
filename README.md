# NetAudit

Repositorio académico grupal del Proyecto de Título de la carrera de Ingeniería en Conectividad y Redes de Duoc UC, sede San Joaquín.

## Equipo

- Axl Urrutia
- Thomas Henriquez
- Maikol Mamani
- Emilio Cortes

## Descripción del proyecto

NetAudit es un asistente orientado al análisis técnico de configuraciones Cisco IOS e IOS XE. El proyecto busca apoyar a administradores de red y equipos de soporte y operación en la detección de configuraciones incorrectas, controles de seguridad ausentes, inconsistencias y malas prácticas.

La solución mantiene un enfoque de solo lectura: recopila información autorizada, la normaliza y la evalúa mediante reglas deterministas. La inteligencia artificial se considera un componente complementario para explicar resultados y recomendaciones; no reemplaza las reglas técnicas ni origina hallazgos por sí sola.

## Estado actual

El desarrollo técnico ha completado los Incrementos 0 a 8. Al cierre del Incremento 8, el sistema dispone de ocho reglas deterministas y una suite de 314 pruebas aprobadas. El Incremento 9, dedicado a la persistencia relacional con PostgreSQL, SQLAlchemy y Alembic, se encuentra definido y planificado, pero aún no implementado.

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
- [Fase 2](Avances-del-Proyecto/Fase-2.md): estructura preparada, pendiente de evidencia.
- [Fase 3](Avances-del-Proyecto/Fase-3.md): estructura preparada, pendiente de evidencia.
- [Historial Git](Avances-del-Proyecto/historial-git.md): explicación cronológica de los commits del proyecto.

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
