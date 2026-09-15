# Historial Git del Proyecto

Este registro explica en español los 54 commits alcanzables desde `HEAD` al momento de la reorganización documental. Conserva el hash abreviado, la fecha, el autor y el mensaje original para mantener trazabilidad con `git log`.

| Fecha | Commit | Autor | Tipo | Mensaje original | Descripción del avance en español |
|---|---|---|---|---|---|
| 2026-07-12 | `b9d6655` | Axl Urrutia | Técnico | `chore: inicializar reglas y seguridad del proyecto` | Inicializa las herramientas, reglas de trabajo y base de seguridad del proyecto. |
| 2026-07-12 | `346b439` | Axl Urrutia | Documentación | `docs: documentar arquitectura reglas y plan incremental` | Documenta la arquitectura, el catálogo de reglas y el plan incremental inicial. |
| 2026-07-12 | `4dc1c79` | Axl Urrutia | Técnico y pruebas | `feat: implementar analizador offline de running-config` | Implementa el analizador offline y sus pruebas iniciales. |
| 2026-07-12 | `de3a22e` | Axl Urrutia | Técnico y pruebas | `feat: agregar metadatos YAML y registro de reglas` | Incorpora metadatos YAML, registro determinista y pruebas asociadas. |
| 2026-07-13 | `edcdbbe` | Axl Urrutia | Técnico y pruebas | `feat: exponer analizador mediante API FastAPI` | Expone el analizador mediante FastAPI y valida la integración con pruebas. |
| 2026-07-14 | `3fac727` | Axl Urrutia | Técnico y pruebas | `feat: agregar recolector Netmiko de solo lectura` | Añade el recolector Netmiko de solo lectura y sus pruebas. |
| 2026-07-14 | `f18aa9d` | axlbuilds | Integración | `Merge pull request #1 from axlbuilds/feature/netmiko-readonly-collector` | Integra mediante la PR 1 el recolector Netmiko de solo lectura. |
| 2026-07-14 | `5366a3a` | Axl Urrutia | Técnico y pruebas | `feat: integrar recolector Netmiko con analizador` | Integra el recolector con el analizador y agrega validaciones automatizadas. |
| 2026-07-14 | `abff23b` | axlbuilds | Integración | `Merge pull request #2 from axlbuilds/feature/netmiko-analyzer-integration` | Integra mediante la PR 2 el análisis obtenido por Netmiko. |
| 2026-07-14 | `5e4ddd4` | Axl Urrutia | Documentación | `docs: registrar cierre del incremento 4` | Registra el cierre técnico y documental del Incremento 4. |
| 2026-07-14 | `67e930d` | axlbuilds | Integración | `Merge pull request #3 from axlbuilds/docs/incremento-4-netmiko` | Integra mediante la PR 3 la documentación del Incremento 4. |
| 2026-07-14 | `0ca7cf3` | Axl Urrutia | Técnico y pruebas | `feat: agregar parsing TextFSM de comandos show` | Añade parsing TextFSM para comandos `show` y las pruebas correspondientes. |
| 2026-07-14 | `b7be551` | axlbuilds | Integración | `Merge pull request #4 from axlbuilds/feature/textfsm-show-parsing` | Integra mediante la PR 4 el parsing operacional con TextFSM. |
| 2026-07-15 | `d79c066` | Axl Urrutia | Documentación | `docs: registrar cierre del incremento 5` | Registra el cierre documental del Incremento 5. |
| 2026-07-15 | `f2fc7ec` | axlbuilds | Integración | `Merge pull request #5 from axlbuilds/docs/incremento-5-textfsm` | Integra mediante la PR 5 la documentación del Incremento 5. |
| 2026-07-21 | `fdeb187` | Axl Urrutia | Documentación | `docs: preparar incremento 6 de análisis integral` | Define la preparación del Incremento 6 de análisis integral. |
| 2026-07-21 | `67b8afe` | axlbuilds | Integración | `Merge pull request #6 from axlbuilds/docs/preparacion-incremento-6` | Integra mediante la PR 6 la preparación documental del Incremento 6. |
| 2026-07-21 | `f7e4398` | Axl Urrutia | Técnico y pruebas | `feat: add full device analysis result contract` | Añade el contrato del resultado integral del dispositivo y sus pruebas. |
| 2026-07-21 | `ae832dd` | Axl Urrutia | Técnico y pruebas | `feat: add strict evidence batch validation` | Añade validación estricta de lotes de evidencias y cobertura automatizada. |
| 2026-07-21 | `92d82fd` | Axl Urrutia | Técnico y pruebas | `feat: add pure full device analysis orchestration` | Implementa la orquestación pura del análisis integral y sus pruebas. |
| 2026-07-21 | `5753768` | Axl Urrutia | Técnico y pruebas | `feat: add full device SSH analysis orchestration` | Integra la orquestación SSH del análisis integral y sus pruebas. |
| 2026-07-22 | `d9bb140` | Axl Urrutia | Documentación | `docs: close increment 6 full device analysis` | Documenta el cierre del Incremento 6 de análisis integral. |
| 2026-07-22 | `2e33184` | axlbuilds | Integración | `Merge pull request #7 from axlbuilds/feature/full-device-analysis` | Integra mediante la PR 7 el análisis integral del dispositivo. |
| 2026-07-22 | `fbd2112` | Axl Urrutia | Técnico y pruebas | `feat: add safe full device API contracts` | Añade contratos seguros para la API integral y sus pruebas. |
| 2026-07-22 | `91aba97` | Axl Urrutia | Técnico y pruebas | `feat: expose safe full device analysis API` | Expone la API segura de análisis integral y valida su comportamiento. |
| 2026-07-22 | `f80ced8` | Axl Urrutia | Documentación | `docs: document increment 7 full device API` | Documenta el Incremento 7 y su API de análisis integral. |
| 2026-07-22 | `f405f57` | axlbuilds | Integración | `Merge pull request #8 from axlbuilds/feature/full-device-api` | Integra mediante la PR 8 la API de análisis integral. |
| 2026-07-22 | `54cf2b0` | Axl Urrutia | Documentación | `docs: define increment 8 deterministic rule expansion` | Define el Incremento 8 de ampliación de reglas deterministas. |
| 2026-07-22 | `cdf2cd8` | Axl Urrutia | Documentación | `docs: add official references for increment 8 rules` | Añade referencias oficiales para las reglas del Incremento 8. |
| 2026-07-29 | `89270a1` | Axl Urrutia | Técnico y pruebas | `feat: expand deterministic running-config rules` | Amplía las reglas deterministas de `running-config` y sus pruebas. |
| 2026-07-30 | `6ebd01d` | Axl Urrutia | Documentación | `docs: close increment 8 deterministic rule expansion` | Documenta el cierre del Incremento 8. |
| 2026-07-30 | `99e0b8c` | Axl Urrutia | Integración | `merge: complete increment 8 deterministic rule expansion` | Fusiona el trabajo completo del Incremento 8. |
| 2026-07-30 | `1264968` | Axl Urrutia | Documentación | `docs: define increment 9 relational persistence` | Define y planifica el Incremento 9 de persistencia relacional. |
| 2026-08-11 | `1daaa3c` | Axl Urrutia | Documentación | `docs: refresh project README` | Actualiza la presentación técnica del proyecto. |
| 2026-08-18 | `bea527d` | thomasdbs21 | Entregable | `Add files via upload` | Incorpora en la raíz la autoevaluación de Thomas Henriquez. |
| 2026-08-18 | `96cd029` | thomasdbs21 | Organización académica | `Create Entregables-APT` | Crea un marcador inicial llamado `Entregables-APT`. |
| 2026-08-18 | `2f092fc` | thomasdbs21 | Organización académica | `Delete Entregables-APT` | Elimina el marcador para dar paso al directorio de entregables. |
| 2026-08-18 | `afd7e4b` | thomasdbs21 | Organización académica | `Create thomas.txt` | Añade un archivo marcador para la carpeta de Thomas. |
| 2026-08-18 | `6e447dd` | ecortesnieva | Entregable | `Add files via upload` | Incorpora la autoevaluación y el diario de reflexión de Emilio Cortes. |
| 2026-08-18 | `ad8db3f` | ecortesnieva | Entregable | `Add files via upload` | Incorpora la definición grupal del proyecto para la Fase 1. |
| 2026-08-20 | `c1698f8` | Axl Urrutia | Integración | `feat: incorporar proyecto Cisco IOS al repositorio grupal` | Incorpora el proyecto técnico y su historial al repositorio grupal. |
| 2026-08-20 | `5606b74` | Axl Urrutia | Organización académica | `docs: organizar carpetas de entregables APT por integrante` | Crea carpetas para cada integrante y para las entregas grupales. |
| 2026-08-20 | `af39d79` | Axl Urrutia | Organización académica | `docs: mover entregables de Emilio Cortes a su carpeta` | Reubica los dos entregables de Emilio Cortes en su carpeta. |
| 2026-08-20 | `25cfc36` | Axl Urrutia | Organización académica | `docs: mover entrega grupal 1.5 a carpeta correspondiente` | Reubica la definición del proyecto en la carpeta grupal. |
| 2026-08-20 | `5ba7021` | Axl Urrutia | Entregable | `docs: agregar entregables individuales de Axl Urrutia` | Incorpora la autoevaluación y el diario de reflexión de Axl Urrutia. |
| 2026-08-20 | `e628cc6` | Axl Urrutia | Documentación | `docs: sanitize and refine increment records` | Sanitiza y mejora los registros documentales de los Incrementos 6 a 8. |
| 2026-08-20 | `a06a442` | Axl Urrutia | Integración | `Merge commit 'e628cc64eafd835bacd549812ca4955e48c7cc6b'` | Integra en el subdirectorio técnico los registros sanitizados. |
| 2026-08-29 | `82a8011` | m41k0l | Entregable | `Autoevaluacion` | Incorpora la autoevaluación de Maikol Mamani en su carpeta. |
| 2026-08-29 | `3d320f6` | m41k0l | Entregable | `DiarioReflexion` | Incorpora el diario de reflexión de Maikol Mamani en su carpeta. |
| 2026-08-31 | `2494bf2` | thomasdbs21 | Entregable | `Add files via upload` | Incorpora una segunda copia de la autoevaluación de Thomas en su carpeta. |
| 2026-08-31 | `3dac27c` | thomasdbs21 | Entregable | `Add files via upload` | Incorpora el diario de reflexión de Thomas Henriquez. |
| 2026-09-07 | `f966220` | thomasdbs21 | Entregable | `Add files via upload` | Incorpora la primera versión de la presentación grupal. |
| 2026-09-07 | `d700070` | thomasdbs21 | Entregable | `Delete Entregables-APT/Entregas Grupales/presentacion_net_audit_apt_corregida.pptx` | Elimina esa primera versión de la presentación grupal. |
| 2026-09-07 | `c0e6d5a` | thomasdbs21 | Entregable | `Add files via upload` | Incorpora la presentación grupal corregida y reparada que se conserva actualmente. |

## Criterio de clasificación

- **Técnico:** implementación de capacidades del sistema.
- **Pruebas:** aparece como **Técnico y pruebas** cuando el mismo commit incorporó o actualizó pruebas; no existe un commit histórico dedicado exclusivamente a pruebas.
- **Documentación:** definición, actualización o cierre documental.
- **Integración:** merges y consolidación de ramas o repositorios.
- **Organización académica:** creación o reubicación de la estructura de entregables.
- **Entregable:** incorporación de documentos individuales o grupales.

Este historial no sustituye a `git log` ni reescribe los commits; lo acompaña con una explicación legible para la revisión académica.
