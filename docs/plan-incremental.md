# Plan incremental de desarrollo

## 1. Propósito

El proyecto se construirá mediante incrementos pequeños, verificables y respaldados por Git. Cada incremento deberá producir una versión funcional o una mejora comprobable, con alcance delimitado y evidencia de validación.

## 2. Principios del desarrollo incremental

- Una tarea por alcance controlado.
- Pruebas pertinentes antes de cerrar un incremento.
- Commits pequeños, coherentes y descriptivos.
- No implementar funciones futuras anticipadamente.
- Revisar seguridad y ausencia de secretos en cada etapa.
- Registrar decisiones en los documentos núcleo (CORE) y en la documentación técnica oficial.
- Validar progresivamente los escenarios en GNS3.
- Incorporar inteligencia artificial solo después de disponer de un motor técnico determinista y validado.

## 3. Incremento 0 — Preparación del repositorio

**Estado:** COMPLETADO.

Incluye:

- Repositorio Git.
- Rama `main`.
- Repositorio privado en GitHub.
- Entorno virtual `.venv`.
- Archivo `.gitignore`.
- Archivo `AGENTS.md`.
- Carpeta `docs`.
- Documentación técnica inicial.

Criterios de cierre:

- Repositorio limpio.
- Primer commit realizado.
- Push realizado a GitHub.
- `.venv` fuera del seguimiento de Git.

## 4. Incremento 1 — Analizador offline de running-config

**Objetivo:** analizar un archivo local `running-config` y producir evaluaciones y `findings` trazables.

Incluye:

- Proyecto Python definido mediante `pyproject.toml`.
- Estructura basada en `src/`.
- `ciscoconfparse2`, usando la clase `CiscoConfParse`.
- Modelos tipados.
- Lectura y hash del archivo.
- Contexto normalizado e inmutable.
- Tres reglas piloto.
- Salida JSON.
- Pruebas con pytest.
- Configuraciones de ejemplo correctas e incorrectas, sin secretos.
- CLI básica.
- README con instalación y uso.

Fuera de alcance:

- SSH y Netmiko.
- FastAPI.
- PostgreSQL, SQLAlchemy y Alembic.
- Streamlit.
- Inteligencia artificial.
- TextFSM y comandos `show`.

Criterios de aceptación:

- Un archivo correcto produce los resultados esperados.
- Un archivo incorrecto preparado para el escenario produce los tres `findings` previstos.
- Una evaluación `PASS` no genera un `Finding`.
- Una evaluación `FAIL` sí genera un `Finding`.
- Los errores de entrada, parsing y reglas se reportan correctamente sin convertirse en resultados falsos.
- Todas las pruebas del incremento están aprobadas.

## 5. Incremento 2 — Registro y metadatos de reglas

Incluye:

- Metadatos en YAML.
- Carga controlada y validada de metadatos.
- Registro de reglas.
- Versionado de definiciones.
- Activación o desactivación de reglas.
- Validación de consistencia entre los metadatos YAML y la lógica Python.

## 6. Incremento 3 — API FastAPI

Incluye:

- Carga de archivos.
- Inicio de análisis.
- Consulta de evaluaciones.
- Consulta de `findings`.
- Manejo estructurado de errores.
- Documentación OpenAPI.

## 7. Incremento 4 — SSH de solo lectura

Incluye:

- Netmiko.
- Lista blanca de comandos autorizados.
- Credenciales obtenidas mediante variables de entorno.
- Conexión con dispositivos del laboratorio GNS3.
- Usuario SSH con privilegios mínimos.
- Manejo de timeouts y errores de conexión.
- Conservación de evidencia original.

No incluye comandos de configuración ni cambios sobre dispositivos.

## 8. Incremento 5 — Comandos show y TextFSM

Incluye:

- Plantillas TextFSM validadas.
- Normalización de evidencia operacional.
- Recopilación de comandos `show` autorizados.
- Estado `NOT_EVALUATED` cuando falte una fuente requerida.
- Primeras reglas operacionales.

## 9. Incremento 6 — Persistencia

Incluye:

- PostgreSQL.
- SQLAlchemy.
- Alembic.
- Entidades `AnalysisRun`, `Device`, `Evidence`, `RuleEvaluation` y `Finding`.
- Historial de análisis.
- Almacenamiento de todas las evaluaciones y únicamente hallazgos derivados de `FAIL`.

## 10. Incremento 7 — Interfaz Streamlit

Incluye:

- Carga de configuraciones.
- Selección de dispositivos.
- Visualización de severidades.
- Presentación de evidencias sanitizadas.
- Recomendaciones técnicas validadas.
- Historial de análisis.

## 11. Incremento 8 — Reportes

Incluye:

- JSON.
- HTML.
- PDF.
- Sanitización de información sensible.
- Resumen por severidad.
- Trazabilidad entre ejecución, evidencia, evaluación y hallazgo.

## 12. Incremento 9 — Inteligencia artificial opcional

Incluye:

- Pasarela independiente del motor de reglas.
- Sanitización previa de datos.
- Entrada estructurada basada en hallazgos validados.
- Explicaciones técnicas.
- Resúmenes.
- Priorización basada exclusivamente en severidades y criterios ya definidos.
- Respuesta técnica alternativa cuando la IA no esté disponible.
- Pruebas destinadas a detectar alucinaciones o alteraciones de resultados.

La IA no creará reglas, hallazgos ni evidencias y no cambiará estados o severidades.

## 13. Incremento 10 — Catálogo MVP y validación GNS3

Incluye:

- Implementación progresiva de 20 a 25 reglas.
- Escenarios correctos e incorrectos en GNS3.
- Medición de verdaderos positivos.
- Revisión de falsos positivos.
- Revisión de falsos negativos.
- Cálculo de `precision`.
- Cálculo de `recall`.
- Medición del tiempo de análisis.
- Evidencias reproducibles para el informe del proyecto.

## 14. Estrategia de Git

- Mantener una rama `main` estable.
- Crear commits por incremento o cambio coherente.
- Utilizar mensajes convencionales cuando corresponda:
  - `feat:` para funcionalidades.
  - `fix:` para correcciones.
  - `test:` para pruebas.
  - `docs:` para documentación.
  - `chore:` para mantenimiento.
  - `refactor:` para cambios internos sin alterar comportamiento.
- Revisar `git diff` antes de cada commit.
- Ejecutar las pruebas pertinentes antes del commit.
- Realizar push solo después de validar el cambio.

No se define todavía un flujo complejo con múltiples ramas.

## 15. Definición de terminado

Una tarea se considera terminada cuando:

- Cumple el alcance acordado.
- No introduce funciones no solicitadas.
- Tiene pruebas cuando corresponde.
- Las pruebas pasan.
- No contiene secretos.
- Está documentada.
- El diff fue revisado.
- Tiene un commit coherente.
- Fue respaldada en GitHub.
- Las decisiones relevantes fueron registradas.

Cuando una tarea solicite explícitamente no realizar commit o push, dichos pasos quedarán pendientes y deberán informarse; la tarea documental podrá considerarse completada en su alcance local, pero no respaldada todavía.

## 16. Riesgos del desarrollo

| Riesgo | Mitigación breve |
|---|---|
| Expansión excesiva del alcance | Delimitar cada incremento y rechazar implementación anticipada. |
| Dependencia de imágenes Cisco | Verificar disponibilidad y licenciamiento antes de planificar escenarios. |
| Falsos positivos | Definir evidencia clara, excepciones y casos de prueba reproducibles. |
| Parsing incompleto | Conservar siempre la fuente original y registrar errores explícitos. |
| Diferencias entre versiones IOS | Registrar plataforma y versión; probar variantes soportadas. |
| Credenciales expuestas | Usar variables de entorno o gestores de secretos y sanitizar salidas. |
| IA que inventa explicaciones | Limitarla a datos validados y probar que no altere resultados. |
| Recursos limitados | Dimensionar el laboratorio y ejecutar escenarios controlados. |
| Dependencias incompatibles | Fijar versiones justificadas y validar en Windows 11 y el futuro Ubuntu Server. |
| Falta de tiempo | Priorizar reglas demostrables y criterios esenciales del MVP. |
| Pérdida de reproducibilidad | Versionar código, metadatos, ejemplos y documentación; registrar el entorno. |

## 17. Próxima acción oficial

La próxima acción oficial será implementar el Incremento 1 mediante Codex, comenzando por una planificación breve y sin implementar componentes futuros.
