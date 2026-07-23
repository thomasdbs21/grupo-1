# Catálogo inicial de reglas Cisco IOS

## 1. Propósito

Este catálogo define reglas destinadas a detectar errores, riesgos, malas prácticas, inconsistencias y controles de seguridad ausentes en configuraciones Cisco IOS. Todas las detecciones serán deterministas, tendrán condiciones explícitas y producirán evidencia verificable.

La inteligencia artificial no será responsable de crear reglas, evaluaciones ni hallazgos. Solo podrá explicar, resumir o priorizar hallazgos previamente validados.

## 2. Estructura de una regla

Cada regla deberá documentar, como mínimo:

- **ID:** identificador único y estable.
- **Versión:** versión de la definición y su lógica.
- **Nombre:** descripción breve del control evaluado.
- **Categoría:** área técnica a la que pertenece.
- **Descripción:** objetivo y alcance de la comprobación.
- **Condición de detección:** criterio determinista para producir cada estado.
- **Fuente requerida:** `running-config` o comando `show` necesario.
- **Plataforma:** dispositivos y versiones a los que aplica.
- **Severidad:** impacto técnico predeterminado.
- **Riesgo técnico:** consecuencia potencial del incumplimiento.
- **Evidencia:** fragmentos y datos que justifican el resultado.
- **Recomendación:** medida técnica validada para revisión del administrador.
- **Referencia:** fuente técnica que respalda el control.
- **Falsos positivos:** situaciones que podrían producir una detección incorrecta.
- **Excepciones:** casos aprobados en los que el control no corresponde.
- **Estado de habilitación:** indica si la regla está activa para una ejecución.

La lógica de evaluación reside exclusivamente en Python; YAML almacena metadatos declarativos. En el Incremento 2, los tres YAML oficiales se cargan de forma segura, se validan y se convierten en objetos `RuleMetadata` inmutables.

El `RuleRegistry` asocia cada ID YAML con una única clase Python, rechaza duplicados e inconsistencias, conserva un orden oficial determinista y ejecuta solamente las habilitadas. El campo `enabled` controla la ejecución, pero no modifica la lógica técnica.

## 3. Estados posibles

- **PASS:** la regla pudo evaluarse y la configuración cumple su condición.
- **FAIL:** la regla pudo evaluarse y detectó un incumplimiento, riesgo, control ausente o mala práctica.
- **NOT_APPLICABLE:** la regla no corresponde al dispositivo, función o configuración analizada.
- **NOT_EVALUATED:** la regla podría aplicar, pero falta una fuente o información necesaria.
- **ERROR:** ocurrió un fallo interno inesperado durante la evaluación.

Todos los estados se almacenan como `RuleEvaluation`. Solo `FAIL` genera un `Finding`.

## 4. Reglas piloto oficiales

### IOS-ADM-001 — Telnet permitido en líneas VTY

- **Categoría:** administración remota.
- **Fuente requerida:** `running-config`.
- **Plataforma:** Cisco IOS e IOSv con líneas VTY.
- **Severidad inicial:** `HIGH`.
- **Condición FAIL:** alguna sección `line vty` permite Telnet. Esto incluye `transport input telnet`, `transport input telnet ssh` y, cuando la lógica y la plataforma definidas determinen que la ausencia de una restricción clara habilita o no impide Telnet, la omisión de `transport input`.
- **Condición PASS:** todas las secciones VTY aplicables restringen el transporte de entrada a SSH y ninguna permite Telnet.
- **Riesgo técnico:** administración remota sin cifrado, con posible exposición de credenciales y sesiones.
- **Recomendación:** restringir el acceso remoto a SSH mediante `transport input ssh`, sujeto a revisión del administrador.
- **Evidencia esperada:** encabezado completo de la sección VTY, líneas `transport input` asociadas y fragmento relevante sin secretos.
- **Posibles falsos positivos:** líneas VTY no accesibles por controles externos, sintaxis heredada dependiente de plataforma o configuraciones parciales.
- **Excepciones:** laboratorio aislado con excepción formal y temporal; aun así, la excepción debe documentarse y no cambia la detección técnica sin política explícita.
- **Validación con ciscoconfparse2:** mediante la clase `CiscoConfParse`, localizar objetos padre que coincidan con `line vty`, consultar sus hijos `transport input` y evaluar todas las secciones VTY, no solo la primera.

Ejemplos inseguros:

```text
line vty 0 4
 transport input telnet
```

```text
line vty 0 4
 transport input telnet ssh
```

Ejemplo recomendado:

```text
line vty 0 4
 transport input ssh
```

Casos esperados:

- **PASS:** existen líneas VTY aplicables y todas permiten únicamente SSH.
- **FAIL:** al menos una sección VTY permite Telnet o incumple la restricción clara según la lógica aprobada.
- **NOT_EVALUATED:** el contenido es insuficiente, incompleto o no permite determinar de forma fiable la política VTY.

### IOS-SRV-001 — Servidor HTTP sin cifrado habilitado

- **Categoría:** servicios innecesarios.
- **Fuente requerida:** `running-config`.
- **Plataforma:** Cisco IOS e IOSv que admitan el servicio HTTP.
- **Severidad inicial:** `MEDIUM`.
- **Condición FAIL:** existe el comando activo `ip http server`.
- **Condición PASS:** el comando activo `ip http server` no existe en una configuración válida y completa.
- **Riesgo técnico:** administración mediante HTTP sin cifrado, con exposición potencial de información y credenciales.
- **Recomendación:** deshabilitar HTTP si no es necesario y evaluar HTTPS cuando corresponda.
- **Evidencia esperada:** línea exacta `ip http server` y su ubicación en la evidencia original.
- **Posibles falsos positivos:** servicio requerido de manera excepcional dentro de una red aislada y compensado por controles externos.
- **Excepciones:** necesidad operacional documentada y aceptada formalmente; no elimina el resultado técnico salvo que la política de excepciones lo contemple.
- **Validación con ciscoconfparse2:** mediante la clase `CiscoConfParse`, buscar una línea activa que coincida exactamente con `ip http server`, excluyendo comentarios y `no ip http server`.

Casos esperados:

- **PASS:** no existe `ip http server` activo.
- **FAIL:** existe `ip http server` activo.

### IOS-AUTH-001 — Enable password sin enable secret

- **Categoría:** contraseñas y autenticación.
- **Fuente requerida:** `running-config`.
- **Plataforma:** Cisco IOS e IOSv cuando utilicen autenticación privilegiada local.
- **Severidad inicial:** `HIGH`.
- **Condición FAIL:** existe `enable password` y no existe `enable secret`.
- **Condición PASS:** existe `enable secret` y no se depende de `enable password`.
- **Condición NOT_APPLICABLE:** la plataforma o el modelo de autenticación validado no utiliza este mecanismo y existe información suficiente para demostrarlo.
- **Riesgo técnico:** protección insuficiente del acceso privilegiado.
- **Recomendación:** utilizar `enable secret` y retirar `enable password` conforme a la política aplicable.
- **Evidencia esperada:** presencia de las directivas, con sus valores completamente enmascarados, y constancia de ausencia o presencia de la alternativa requerida.
- **Posibles falsos positivos:** configuraciones parciales, autenticación externa con una política distinta o sintaxis específica de una versión no contemplada.
- **Excepciones:** plataformas sin soporte del mecanismo o política formal de autenticación externa demostrable.
- **Validación con ciscoconfparse2:** mediante la clase `CiscoConfParse`, buscar directivas activas `enable password` y `enable secret` en el nivel global, comparar su presencia y sanitizar cualquier valor antes de registrar evidencia.

Ejemplo inseguro sin contraseña real:

```text
enable password <VALOR_ENMASCARADO>
```

Ejemplo recomendado sin secreto real:

```text
enable secret <VALOR_ENMASCARADO>
```

Casos esperados:

- **PASS:** existe `enable secret` y no se depende de `enable password`.
- **FAIL:** existe `enable password` sin `enable secret`.
- **NOT_APPLICABLE:** el mecanismo no corresponde a la plataforma o esquema de autenticación demostrado.

## 5. Reglas aprobadas para el Incremento 8

Las siguientes reglas están formalmente aprobadas, pero todavía no están implementadas. Utilizarán exclusivamente `running-config`, recibirán `AnalysisContext` inmutable y se incorporarán al `RuleRegistry` existente. Sus excepciones inesperadas producirán `ERROR`; todas sus evaluaciones se conservarán y únicamente `FAIL` generará un `Finding`.

### IOS-ADM-002 — SSH versión 1 habilitada

- **Categoría:** administración remota.
- **Fuente requerida:** `running-config`.
- **Plataforma:** Cisco IOS e IOS XE con configuración explícita de versión SSH.
- **Severidad:** `HIGH`.
- **Condición FAIL:** existe una directiva activa y exacta `ip ssh version 1`. Esta condición prevalece si también aparece una directiva de versión 2.
- **Condición PASS:** existe una directiva activa y exacta `ip ssh version 2` y no existe `ip ssh version 1`.
- **Condición NOT_EVALUATED:** no existe ninguna directiva explícita de versión SSH.
- **Criterio de seguridad:** no se infiere como segura una versión predeterminada.
- **Evidencia FAIL:** únicamente la directiva detectada y su número de línea; no se incluyen claves SSH ni salidas operacionales.
- **Riesgo técnico:** uso permitido de una versión heredada del protocolo SSH.
- **Posibles falsos positivos:** configuración parcial o sintaxis específica de plataforma no contemplada.
- **Referencia técnica:** [Cisco IOS XE 17.x — Secure Shell Version 2 Support](https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/sec-vpn/b-security-vpn/m_sec-secure-shell-v2-0.html).

### IOS-SRV-002 — Servicios TCP/UDP pequeños habilitados

- **Categoría:** servicios innecesarios.
- **Fuente requerida:** `running-config`.
- **Plataforma:** Cisco IOS e IOS XE que admitan servicios TCP/UDP pequeños.
- **Severidad:** `MEDIUM`.
- **Condición FAIL:** existe una o ambas directivas activas y exactas `service tcp-small-servers` y `service udp-small-servers`.
- **Condición PASS:** no existe ninguna de esas directivas activas.
- **Condición NOT_APPLICABLE:** no se utiliza.
- **Directivas negadas:** `no service tcp-small-servers` y `no service udp-small-servers` no producen `FAIL`.
- **Evidencia:** exclusivamente las directivas inseguras activas encontradas y sus números de línea.
- **Riesgo técnico:** exposición innecesaria de servicios pequeños TCP o UDP.
- **Posibles falsos positivos:** necesidad operacional excepcional y formalmente aceptada en un entorno controlado.
- **Referencia técnica:** [Cisco IOS XE 17.x — Performing Basic System Management](https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/syst-mgmt/b-system-management/m_bsm-basic-sys-manage-xe.html).

### IOS-NTP-001 — Servidor NTP no configurado

- **Categoría:** NTP.
- **Fuente requerida:** `running-config`.
- **Plataforma:** Cisco IOS e IOS XE que admitan configuración NTP.
- **Severidad:** `MEDIUM`.
- **Condición PASS:** existe al menos una directiva activa y válida `ntp server` con un destino.
- **Condición FAIL:** no existe ningún servidor NTP activo.
- **Contrato de entrada:** la evaluación parte del contrato vigente de `running-config` completo y no incorpora heurísticas nuevas de completitud.
- **Evidencia PASS:** indicación genérica `servidor NTP: configurado`.
- **Evidencia FAIL:** texto sintético seguro `servidor NTP: no configurado`.
- **Sanitización:** no se exponen direcciones, hostnames, claves ni parámetros sensibles.
- **Riesgo técnico:** ausencia de una fuente de tiempo remota configurada para correlación y trazabilidad temporal.
- **Posibles falsos positivos:** sincronización provista por un mecanismo de plataforma no representado mediante `ntp server`.
- **Referencia técnica:** [Cisco IOS XE 17.x — Network Time Protocol](https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/syst-mgmt/b-system-management/m_bsm-time-calendar-set.html).

### IOS-LOG-001 — Servidor Syslog no configurado

- **Categoría:** Syslog.
- **Fuente requerida:** `running-config`.
- **Plataforma:** Cisco IOS e IOS XE con destinos remotos de logging.
- **Severidad:** `MEDIUM`.
- **Condición PASS:** existe al menos un destino remoto activo con una sintaxis soportada.
- **Condición FAIL:** no existe ningún destino remoto ni indicio de una sintaxis de destino no reconocida.
- **Condición NOT_EVALUATED:** existe una posible sintaxis activa de destino remoto que no puede reconocerse con seguridad; se evita convertirla en un falso `FAIL`.
- **Sintaxis moderna soportada:** `logging host <destino> [opciones soportadas]`.
- **Sintaxis heredada soportada:** `logging <destino>`.
- **Exclusiones de la sintaxis heredada:** no son destinos remotos directivas como `logging buffered`, `logging console`, `logging monitor`, `logging trap`, `logging facility`, `logging source-interface`, `logging origin-id`, `logging discriminator`, `logging history`, `logging rate-limit` o `logging queue-limit`.
- **Directivas negadas:** las formas iniciadas por `no logging` no configuran un destino activo.
- **Evidencia PASS:** indicación genérica `servidor Syslog remoto: configurado`.
- **Evidencia FAIL:** texto sintético seguro `servidor Syslog remoto: no configurado`.
- **Sanitización:** no se exponen destino, VRF, dirección, hostname ni opciones asociadas.
- **Riesgo técnico:** ausencia de envío remoto de eventos para supervisión y trazabilidad.
- **Posibles falsos positivos:** variantes de sintaxis dependientes de plataforma todavía no reconocidas; deben conducir a `NOT_EVALUATED` cuando se detecte un indicio.
- **Referencias técnicas:**
  - [Cisco IOS Embedded Syslog Manager Command Reference — logging host](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/esm/command/esm-cr-book/esm-cr-a1.html).
  - [Cisco IOS XE 17.17.x — Configuring System Message Logs](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9600/software/release/17-17/configuration_guide/sys_mgmt/b_1717_sys_mgmt_9600_cg/configuring_system_message_logs.html).

## 6. Catálogo previsto para el MVP

Los identificadores, severidades y prioridades no piloto continúan preliminares, excepto las cuatro reglas aprobadas para el Incremento 8. Sus contratos oficiales están definidos en la sección anterior.

| ID provisional | Nombre | Categoría | Fuente requerida | Severidad preliminar | Prioridad MVP | Estado |
|---|---|---|---|---|---|---|
| IOS-ADM-001 | Telnet permitido en líneas VTY | Administración remota | `running-config` | HIGH | Alta | PILOTO |
| IOS-ADM-002 | SSH versión 1 habilitada | Administración remota | `running-config` | HIGH | Alta | INCREMENTO 8 APROBADO |
| IOS-AUTH-001 | Enable password sin enable secret | Contraseñas y autenticación | `running-config` | HIGH | Alta | PILOTO |
| IOS-AUTH-002 | Contraseña de consola ausente o no protegida | Contraseñas y autenticación | `running-config` | MEDIUM | Media | MVP |
| IOS-SRV-001 | Servidor HTTP sin cifrado habilitado | Servicios innecesarios | `running-config` | MEDIUM | Alta | PILOTO |
| IOS-SRV-002 | Servicios TCP/UDP pequeños habilitados | Servicios innecesarios | `running-config` | MEDIUM | Media | INCREMENTO 8 APROBADO |
| IOS-INT-001 | Interfaz no utilizada sin shutdown | Interfaces | `running-config`, `show interfaces` | MEDIUM | Media | MVP |
| IOS-INT-002 | Descripción ausente en interfaz activa | Interfaces | `running-config`, `show interfaces` | LOW | Baja | MVP |
| IOS-VLAN-001 | VLAN 1 utilizada para acceso de usuarios | VLAN | `running-config`, `show vlan brief` | MEDIUM | Media | MVP |
| IOS-VLAN-002 | VLAN sin nombre descriptivo | VLAN | `running-config`, `show vlan brief` | LOW | Baja | FUTURA |
| IOS-TRUNK-001 | VLAN nativa predeterminada en trunk | Enlaces troncales | `running-config`, `show interfaces trunk` | MEDIUM | Alta | MVP |
| IOS-TRUNK-002 | VLAN permitidas sin restricción en trunk | Enlaces troncales | `running-config`, `show interfaces trunk` | HIGH | Alta | MVP |
| IOS-STP-001 | PortFast ausente en puerto de acceso | Spanning Tree | `running-config`, `show spanning-tree` | MEDIUM | Media | MVP |
| IOS-STP-002 | BPDU Guard ausente en puerto PortFast | Spanning Tree | `running-config`, `show spanning-tree` | HIGH | Alta | MVP |
| IOS-IP-001 | Dirección IP duplicada en el contexto | Direccionamiento IP | Contexto de múltiples dispositivos | HIGH | Media | FUTURA |
| IOS-ACL-001 | ACL con permiso any any | ACL | `running-config`, `show access-lists` | HIGH | Alta | MVP |
| IOS-ACL-002 | ACL definida pero no aplicada | ACL | `running-config`, `show access-lists` | MEDIUM | Media | MVP |
| IOS-OSPF-001 | Autenticación OSPF ausente | OSPF | `running-config` | HIGH | Alta | MVP |
| IOS-OSPF-002 | Vecino OSPF esperado no establecido | OSPF | `show ip ospf neighbor` | HIGH | Media | FUTURA |
| IOS-NTP-001 | Servidor NTP no configurado | NTP | `running-config` | MEDIUM | Alta | INCREMENTO 8 APROBADO |
| IOS-NTP-002 | Asociación NTP no sincronizada | NTP | `show ntp associations` | MEDIUM | Media | FUTURA |
| IOS-LOG-001 | Servidor Syslog no configurado | Syslog | `running-config` | MEDIUM | Alta | INCREMENTO 8 APROBADO |
| IOS-SNMP-001 | Comunidad SNMP insegura o predeterminada | SNMP | `running-config` | HIGH | Alta | MVP |
| IOS-AVL-001 | Interfaz operativa con errores elevados | Disponibilidad | `show interfaces` | HIGH | Media | FUTURA |
| IOS-DOC-001 | Hostname genérico o ausente | Documentación y nomenclatura | `running-config` | LOW | Baja | MVP |

## 7. Reglas basadas en running-config

Pueden evaluarse exclusivamente con una configuración completa, entre otras:

- Telnet permitido en líneas VTY.
- SSH versión 1 habilitada.
- `enable password` sin `enable secret`.
- Servidor HTTP sin cifrado habilitado.
- Servicios innecesarios configurados.
- Autenticación OSPF ausente, cuando la configuración contenga todo el contexto requerido.
- Servidor NTP no configurado.
- Servidor Syslog no configurado.
- Comunidades SNMP inseguras, siempre con valores sanitizados.
- Hostname genérico o ausente.

Las reglas que dependan del estado operacional, de la aplicación efectiva de una configuración o de relaciones entre dispositivos no deben inferirse únicamente desde `running-config`.

## 8. Reglas que requieren comandos show

En incrementos futuros, algunas reglas necesitarán evidencia operacional:

- `show interfaces`: estado, contadores de errores, uso real y disponibilidad de interfaces.
- `show interfaces trunk`: trunks operativos, VLAN nativa y VLAN permitidas efectivas.
- `show vlan brief`: existencia, nombre, estado y asociación operacional de VLAN.
- `show spanning-tree`: roles, estados, raíz y controles STP efectivos.
- `show ip ospf neighbor`: formación y estado de adyacencias OSPF.
- `show access-lists`: contadores y presencia operacional de ACL.
- `show ntp associations`: sincronización y asociaciones NTP.
- `show logging`: estado y destinos efectivos de Syslog.

Cuando una regla requiera una de estas fuentes y no esté disponible, deberá producir `NOT_EVALUATED`, no `PASS` ni `FAIL`.

## 9. Criterios para seleccionar reglas del MVP

- Relevancia técnica para redes Cisco IOS.
- Posibilidad de demostrar el control en un laboratorio virtual autorizado; GNS3 con IOSv o IOSvL2 permanece como opción futura condicionada a disponer legalmente de imágenes compatibles.
- Baja subjetividad y condición determinista explícita.
- Evidencia clara, trazable y sanitizable.
- Referencias técnicas disponibles.
- Riesgo representativo para confidencialidad, integridad o disponibilidad.
- Complejidad de implementación compatible con el tiempo del MVP.
- Posibilidad de construir casos reproducibles `PASS` y `FAIL`.
- Capacidad de controlar y documentar falsos positivos.

## 10. Decisiones pendientes

- Severidades definitivas de las reglas no piloto y no aprobadas para el Incremento 8.
- Referencias técnicas definitivas para las reglas futuras que todavía no cuentan con fuentes oficiales específicas; las cuatro reglas del Incremento 8 ya tienen referencias aprobadas.
- Excepciones y política formal para administrarlas.
- Reglas que requerirán contexto entre dispositivos.
- Reglas operacionales que entrarán finalmente al MVP.
- Revisión y validación del catálogo con el docente.
