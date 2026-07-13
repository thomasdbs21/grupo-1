# Proyecto: Auditor de configuraciones Cisco IOS

## 1. Propósito del proyecto

Desarrollar un asistente para analizar configuraciones de dispositivos Cisco IOS, detectar errores, inconsistencias, riesgos, controles de seguridad ausentes y malas prácticas, y entregar recomendaciones técnicas explicadas.

El foco principal del proyecto es conectividad y redes.

La programación, la ciberseguridad y la inteligencia artificial son componentes complementarios utilizados para automatizar el análisis, estructurar la evidencia y explicar los resultados.

El sistema no administrará ni modificará automáticamente los dispositivos.

---

## 2. Objetivo funcional

El sistema deberá poder recibir configuraciones Cisco IOS mediante:

- Archivos locales `running-config`.
- Conexión SSH de solo lectura, en incrementos posteriores.
- Salidas de comandos `show`, en incrementos posteriores.

Después deberá:

1. Validar la entrada.
2. Conservar la salida original.
3. Analizar y normalizar la información.
4. Ejecutar reglas técnicas deterministas.
5. Registrar el resultado de cada regla.
6. Crear hallazgos cuando exista un incumplimiento.
7. Conservar evidencia técnica y trazabilidad.
8. Presentar recomendaciones validadas.
9. Utilizar inteligencia artificial opcionalmente para explicar los hallazgos.
10. Generar resultados estructurados y reportes.

---

## 3. Tipos de análisis

El sistema deberá poder detectar:

- Configuraciones incorrectas.
- Configuraciones inseguras.
- Controles de seguridad ausentes.
- Servicios innecesarios o inseguros.
- Inconsistencias entre configuraciones relacionadas.
- Malas prácticas técnicas.
- Configuraciones funcionales que puedan mejorarse.
- Riesgos para la administración remota.
- Riesgos para la confidencialidad.
- Riesgos para la integridad.
- Riesgos para la disponibilidad.
- Problemas de autenticación y protección de credenciales.
- Problemas en interfaces.
- Problemas de VLAN y enlaces troncales.
- Problemas relacionados con Spanning Tree.
- Problemas de direccionamiento IP.
- Problemas en listas de control de acceso.
- Problemas en OSPF.
- Ausencia o mala configuración de NTP.
- Ausencia o mala configuración de Syslog.
- Riesgos relacionados con SNMP.
- Falta de documentación o nomenclatura.
- Problemas operacionales detectados mediante comandos `show`, en incrementos posteriores.

Toda detección deberá estar respaldada por:

- Una regla determinista.
- Una condición de evaluación explícita.
- Evidencia técnica.
- Una severidad definida.
- Una recomendación técnica validada.
- Una referencia técnica, cuando corresponda.

La inteligencia artificial no será la fuente original de los hallazgos.

---

## 4. Principios obligatorios

- El sistema será de solo lectura.
- No ejecutará cambios automáticos sobre dispositivos.
- No ingresará al modo de configuración.
- No ejecutará comandos destructivos.
- No guardará configuraciones en los dispositivos.
- No reiniciará dispositivos.
- No eliminará archivos ni configuraciones.
- No aplicará recomendaciones automáticamente.
- El administrador de red será responsable de revisar y aplicar cualquier cambio.
- El motor de reglas será determinista.
- Un mismo contexto de entrada deberá producir resultados técnicos equivalentes.
- La inteligencia artificial no decidirá por sí sola si una configuración es correcta o incorrecta.
- La inteligencia artificial no inventará hallazgos.
- El análisis deberá funcionar aunque la inteligencia artificial no esté disponible.

---

## 5. Arquitectura tecnológica oficial

### Plataforma del laboratorio

- Sistema anfitrión: Windows 11.
- Virtualización: VMware Workstation.
- Laboratorio de red: GNS3 y GNS3 VM.
- Routers virtuales: Cisco IOSv.
- Switches virtuales: Cisco IOSvL2.
- Servidor del asistente: Ubuntu Server.
- Equipos de prueba: VPCS o clientes Linux.

### Desarrollo

- Lenguaje principal: Python 3.
- Estructura de proyecto: diseño basado en carpeta `src/`.
- Parsing de `running-config`: CiscoConfParse.
- Parsing futuro de comandos `show`: TextFSM.
- Conexión SSH futura: Netmiko.
- API futura: FastAPI y Uvicorn.
- Validación de modelos: Pydantic.
- Base de datos futura: PostgreSQL.
- ORM futuro: SQLAlchemy.
- Migraciones futuras: Alembic.
- Interfaz futura del MVP: Streamlit.
- Metadatos de reglas: YAML.
- Lógica de reglas: Python.
- Pruebas: pytest.
- Reportes futuros: Jinja2, HTML, PDF y JSON.
- Inteligencia artificial: pasarela opcional compatible con modelo local o API externa.
- Control de versiones: Git.

---

## 6. Separación de responsabilidades

El proyecto deberá mantener separados los siguientes componentes:

1. Entrada de archivos.
2. Recopilación SSH.
3. Parsing.
4. Normalización.
5. Contexto de análisis.
6. Motor de reglas.
7. Almacenamiento.
8. API.
9. Interfaz.
10. Reportes.
11. Pasarela de inteligencia artificial.

Ningún componente deberá asumir responsabilidades que pertenezcan a otro módulo sin una justificación técnica explícita.

---

## 7. Aislamiento obligatorio de las reglas

Las reglas:

- No tendrán acceso directo a Netmiko.
- No abrirán conexiones SSH.
- No ejecutarán comandos en dispositivos.
- No tendrán acceso directo a PostgreSQL.
- No utilizarán directamente SQLAlchemy.
- No escribirán archivos arbitrarios.
- No invocarán la pasarela de inteligencia artificial.
- No enviarán datos a servicios externos.
- No modificarán el contexto recibido.
- No modificarán otras evaluaciones.
- No crearán credenciales.
- No alterarán la severidad definida por otra regla.

Las reglas solo recibirán un contexto normalizado e inmutable.

Cada regla deberá producir un resultado estructurado y determinista.

---

## 8. Contexto normalizado

El contexto de análisis deberá representar de forma estructurada la información obtenida desde:

- `running-config`.
- Comandos `show`.
- Metadatos del dispositivo.
- Resultados del parsing.
- Errores de recopilación.
- Errores de parsing.
- Fuentes de evidencia disponibles.

El contexto deberá ser inmutable durante la evaluación de las reglas.

Las reglas no deberán analizar directamente conexiones SSH ni interactuar con dispositivos.

---

## 9. Estados de evaluación

Toda regla deberá terminar en uno de los siguientes estados:

### PASS

La regla pudo evaluarse y la configuración cumple con la condición técnica definida.

### FAIL

La regla pudo evaluarse y detectó un incumplimiento, riesgo, ausencia de control o mala práctica.

### NOT_APPLICABLE

La regla no corresponde al tipo de dispositivo, función o configuración analizada.

Ejemplo:

Una regla de OSPF no aplica a un switch de acceso que no ejecuta enrutamiento dinámico.

### NOT_EVALUATED

La regla podría aplicar, pero no existe información suficiente para evaluarla.

Ejemplo:

La regla requiere `show ip ospf neighbor`, pero ese comando no fue recopilado.

### ERROR

Se produjo un fallo inesperado durante la evaluación de la regla.

Los errores de programación no deberán convertirse silenciosamente en `PASS`, `FAIL` o `NOT_EVALUATED`.

---

## 10. Evaluaciones y hallazgos

`rule_evaluations` deberá almacenar el resultado de todas las reglas ejecutadas, incluyendo:

- PASS.
- FAIL.
- NOT_APPLICABLE.
- NOT_EVALUATED.
- ERROR.

`findings` deberá almacenar únicamente incumplimientos derivados de evaluaciones con estado `FAIL`.

Ejemplo de incumplimiento:

    Regla evaluada: IOS-ADM-001
    Estado: FAIL
    Resultado en rule_evaluations: se almacena
    Resultado en findings: se crea un hallazgo

Ejemplo de cumplimiento:

    Regla evaluada: IOS-ADM-001
    Estado: PASS
    Resultado en rule_evaluations: se almacena
    Resultado en findings: no se crea un hallazgo

No deberán crearse hallazgos para reglas `PASS`, `NOT_APPLICABLE`, `NOT_EVALUATED` o `ERROR`.

---

## 11. Severidad

Las severidades técnicas serán definidas previamente por el catálogo de reglas.

Valores esperados:

- INFO.
- LOW.
- MEDIUM.
- HIGH.
- CRITICAL.

La inteligencia artificial no podrá modificar la severidad.

Cuando la IA priorice o resuma hallazgos, deberá utilizar la severidad y los criterios ya definidos por el motor de reglas.

---

## 12. Evidencia y trazabilidad

Cada evidencia deberá poder conservar:

- Identificador de evidencia.
- Identificador de ejecución.
- Identificador del dispositivo.
- Nombre del dispositivo.
- Plataforma.
- Fuente de la información.
- Comando ejecutado, cuando corresponda.
- Fecha y hora de recopilación.
- Salida original.
- Salida normalizada.
- Fragmento relevante.
- Hash de integridad.
- Estado del parsing.
- Error de parsing, cuando exista.
- Regla que utilizó la evidencia.

La salida original deberá conservarse aunque el parsing haya sido exitoso.

Los hallazgos deberán permitir identificar claramente por qué una regla produjo un resultado `FAIL`.

---

## 13. Seguridad de credenciales y datos sensibles

Nunca se deberán incluir credenciales reales dentro del repositorio.

No se deberán almacenar en texto plano:

- Contraseñas.
- Secretos de modo privilegiado.
- Claves privadas.
- Tokens.
- Claves API.
- Comunidades SNMP.
- Códigos de recuperación.

Las credenciales y secretos no deberán aparecer en:

- Logs.
- Reportes.
- Salidas de consola.
- Mensajes de error.
- Pruebas unitarias.
- Archivos de ejemplo.
- Capturas de pantalla.
- Solicitudes enviadas a la inteligencia artificial.
- Respuestas de la API.
- Commits de Git.

Los archivos `.env` deberán estar excluidos mediante `.gitignore`.

Solo podrá versionarse un archivo `.env.example` sin valores reales.

Antes de enviar información a la inteligencia artificial, deberá aplicarse sanitización o eliminación de datos sensibles.

---

## 14. Restricciones de comandos de red

En los incrementos que utilicen SSH, solamente podrán ejecutarse comandos previamente autorizados mediante una lista blanca.

Ejemplos de comandos permitidos:

    show running-config
    show version
    show ip interface brief
    show interfaces
    show interfaces status
    show interfaces trunk
    show vlan brief
    show spanning-tree
    show ip ospf neighbor
    show ip route
    show access-lists
    show ntp associations
    show logging
    show snmp

Ejemplos de comandos prohibidos:

    configure terminal
    conf t
    write memory
    copy running-config startup-config
    reload
    erase
    delete
    shutdown
    no shutdown
    debug all

No se aceptarán comandos arbitrarios proporcionados directamente por el usuario sin validación.

---

## 15. Inteligencia artificial

La pasarela de inteligencia artificial será opcional e independiente del motor técnico.

La inteligencia artificial podrá:

- Explicar por qué una configuración representa un riesgo.
- Explicar qué control de seguridad está ausente.
- Describir el posible impacto técnico.
- Explicar por qué una recomendación es más segura.
- Resumir hallazgos.
- Organizar los hallazgos utilizando severidades ya definidas.
- Adaptar las explicaciones a lenguaje técnico o educativo.
- Responder preguntas sobre hallazgos existentes.
- Explicar conceptos relacionados con Cisco IOS.
- Relacionar un hallazgo con su evidencia.
- Ayudar a interpretar una recomendación ya validada.

La inteligencia artificial no podrá:

- Decidir por sí sola si una configuración cumple.
- Inventar reglas.
- Inventar hallazgos.
- Crear evidencia inexistente.
- Alterar el estado de una regla.
- Alterar la severidad.
- Alterar la evidencia.
- Alterar el identificador de la regla.
- Alterar la recomendación técnica validada.
- Cambiar resultados almacenados.
- Ejecutar comandos en dispositivos.
- Aplicar configuraciones.
- Solicitar o revelar credenciales.

El sistema deberá conservar una explicación técnica básica proveniente de la regla, de modo que los resultados puedan visualizarse aunque la inteligencia artificial no esté disponible.

---

## 16. Reglas técnicas

Cada regla deberá tener como mínimo:

- Identificador único.
- Versión.
- Nombre.
- Categoría.
- Descripción.
- Condición de detección.
- Fuente requerida.
- Plataformas aplicables.
- Severidad predeterminada.
- Riesgo técnico.
- Recomendación.
- Evidencia esperada.
- Referencia técnica.
- Posibles falsos positivos.
- Excepciones.
- Estado de habilitación.

Los metadatos podrán almacenarse en YAML.

La lógica de evaluación deberá implementarse en Python.

No se deberá intentar representar lógica compleja exclusivamente mediante YAML.

---

## 17. Categorías del catálogo de reglas

El catálogo podrá incluir reglas de:

- Administración remota.
- Contraseñas y autenticación.
- Servicios innecesarios.
- Interfaces.
- VLAN.
- Enlaces troncales.
- Spanning Tree.
- Direccionamiento IP.
- Listas de control de acceso.
- OSPF.
- NTP.
- Syslog.
- SNMP.
- Disponibilidad.
- Documentación y nomenclatura.

El catálogo completo podrá contener aproximadamente 30 reglas.

El MVP deberá priorizar entre 20 y 25 reglas técnicamente demostrables dentro del laboratorio GNS3.

---

## 18. Primer incremento funcional

El primer incremento analizará únicamente archivos locales `running-config`.

Debe incluir:

- Lectura de archivo local.
- Validación de la ruta y formato básico.
- Conservación del contenido original.
- Cálculo de hash.
- Parsing mediante CiscoConfParse.
- Creación de un contexto normalizado e inmutable.
- Ejecución de dos o tres reglas piloto.
- Estados de evaluación.
- Registro de todas las evaluaciones.
- Creación de hallazgos únicamente desde resultados `FAIL`.
- Salida estructurada en JSON.
- Manejo claro de errores.
- Pruebas unitarias con pytest.
- Archivos de ejemplo correctos e incorrectos.
- Documentación básica de instalación y ejecución.

---

## 19. Reglas piloto iniciales

### IOS-ADM-001: Telnet permitido en líneas VTY

Detectar líneas VTY que permitan Telnet.

Ejemplo inseguro:

    line vty 0 4
     transport input telnet ssh

Resultado esperado:

- Estado: FAIL.
- Riesgo: administración remota sin cifrado mediante Telnet.
- Recomendación: permitir únicamente SSH.

Ejemplo recomendado:

    line vty 0 4
     transport input ssh

### IOS-SRV-001: Servidor HTTP sin cifrado habilitado

Detectar:

    ip http server

Resultado esperado:

- Estado: FAIL.
- Riesgo: servicio HTTP de administración sin cifrado.
- Recomendación: deshabilitar HTTP si no es necesario y evaluar HTTPS cuando corresponda.

### IOS-AUTH-001: Uso de enable password sin enable secret

Detectar el uso de:

    enable password

cuando no exista:

    enable secret

Resultado esperado:

- Estado: FAIL.
- Riesgo: protección insuficiente del acceso privilegiado.
- Recomendación: utilizar `enable secret` y eliminar el uso de `enable password`, según la política aplicable.

---

## 20. Elementos fuera del primer incremento

No implementar todavía:

- Conexión SSH.
- Netmiko.
- Recopilación automática desde GNS3.
- PostgreSQL.
- SQLAlchemy.
- Alembic.
- FastAPI.
- Uvicorn.
- Streamlit.
- TextFSM.
- Comandos `show`.
- Ollama.
- API externa de inteligencia artificial.
- Reportes PDF.
- Autenticación de usuarios.
- Modificación de dispositivos.
- Catálogo completo de reglas.
- Sistemas distribuidos.
- Celery.
- Redis.
- Alta disponibilidad.

Estos componentes se agregarán en incrementos posteriores.

---

## 21. Plan incremental

### Incremento 1

- Archivo `running-config`.
- CiscoConfParse.
- Tres reglas piloto.
- Salida JSON.
- pytest.

### Incremento 2

- Metadatos YAML.
- Registro de reglas.
- Carga controlada de reglas.
- Más pruebas unitarias.

### Incremento 3

- FastAPI.
- Carga de archivos mediante API.
- Consulta de evaluaciones y hallazgos.

### Incremento 4

- Netmiko.
- SSH de solo lectura.
- Lista blanca de comandos.
- Recopilación desde GNS3.

### Incremento 5

- TextFSM.
- Comandos `show`.
- Evidencia operacional.

### Incremento 6

- PostgreSQL.
- SQLAlchemy.
- Alembic.
- Historial de análisis.

### Incremento 7

- Streamlit.
- Visualización de resultados.
- Selección de dispositivos.
- Historial.

### Incremento 8

- Reportes HTML, JSON y PDF.

### Incremento 9

- Pasarela opcional de inteligencia artificial.
- Sanitización de datos.
- Explicaciones de hallazgos.

### Incremento 10

- Implementación progresiva de 20 a 25 reglas.
- Validación completa en GNS3.
- Medición de precisión.
- Revisión de falsos positivos y falsos negativos.

---

## 22. Normas de desarrollo

- Utilizar type hints.
- Mantener funciones pequeñas y enfocadas.
- Utilizar nombres descriptivos.
- Separar dominio, parsing, reglas, servicios e infraestructura.
- Evitar dependencias innecesarias.
- No duplicar lógica.
- Crear pruebas para cada comportamiento importante.
- No ocultar errores mediante bloques `except` genéricos.
- No convertir errores internos en resultados técnicos falsos.
- No modificar la arquitectura oficial sin explicarlo.
- No ampliar el alcance de una tarea sin autorización.
- No implementar funciones futuras anticipadamente.
- No incluir credenciales o datos sensibles.
- No agregar dependencias sin justificar su uso.
- Preferir implementaciones simples y mantenibles para el MVP.
- Ejecutar solamente comandos necesarios para implementar o validar una tarea.
- Preferir pruebas específicas antes de ejecutar repetidamente toda la suite.
- Ejecutar las pruebas antes de declarar una tarea completada.
- Informar qué archivos fueron creados o modificados.
- Informar qué comandos fueron ejecutados.
- Informar qué pruebas fueron ejecutadas.
- Informar claramente cualquier limitación pendiente.

---

## 23. Instrucciones para Codex

Antes de modificar el repositorio, Codex deberá:

1. Leer este archivo `AGENTS.md`.
2. Revisar los documentos relacionados dentro de `docs/`.
3. Revisar el estado actual del repositorio.
4. Entender el incremento solicitado.
5. Presentar un plan breve cuando la tarea afecte varios archivos.

Durante una tarea, Codex deberá:

- Limitarse al alcance solicitado.
- No crear componentes futuros sin autorización.
- No modificar decisiones oficiales silenciosamente.
- No ejecutar comandos destructivos.
- No introducir credenciales.
- No reemplazar reglas deterministas por decisiones de inteligencia artificial.
- No asumir que una configuración es insegura sin una regla definida.
- Mantener compatibilidad con Windows durante el primer incremento.
- Mantener el diseño preparado para Ubuntu Server en incrementos posteriores.

Al finalizar una tarea, Codex deberá indicar:

- Resumen de los cambios.
- Archivos creados.
- Archivos modificados.
- Dependencias agregadas.
- Comandos ejecutados.
- Pruebas ejecutadas.
- Resultado de las pruebas.
- Limitaciones o tareas pendientes.

---

## 24. Fuente oficial de decisiones

Este archivo representa las restricciones generales que Codex deberá respetar.

Las decisiones más detalladas deberán mantenerse en:

    docs/decisiones-tecnicas.md
    docs/arquitectura.md
    docs/catalogo-reglas.md
    docs/plan-incremental.md

Si existe una contradicción entre una instrucción puntual y las restricciones de seguridad de este archivo, deberá detenerse la implementación y solicitar aclaración antes de continuar.
