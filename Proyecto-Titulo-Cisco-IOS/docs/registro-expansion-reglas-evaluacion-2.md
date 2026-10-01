# Expansión determinista para la Evaluación 2

Preparación: 1 de octubre de 2026. Amplía la campaña inicial sin asignar un
nuevo número de incremento ni implementar la persistencia planificada.

Este registro conserva la expansión estática de 12 reglas/13 evaluaciones y
sus resultados históricos. La ampliación operacional autorizada posteriormente
se documenta en [registro operacional](registro-expansion-operacional-evaluacion-2.md):
El primer corte operacional tuvo 18 evaluaciones; el [corte vigente](registro-controles-adicionales-evaluacion-2.md)
tiene 21 y conserva ocho comandos con campaña integral offline. El bloqueo de permisos
descrito al final de este registro fue resuelto por autorización explícita posterior.

## Objetivo y contratos

Las reglas detectan. La evidencia demuestra. La IA explica. En este corte
no se implementa IA. Se agregan cinco controles exclusivamente de
`running-config`, con `AnalysisContext` inmutable y metadatos versión 1.0.0.
Las siete reglas previas no cambian su lógica.

| ID | Severidad | Contrato determinista |
|---|---|---|
| IOS-AUTH-002 | MEDIUM | PASS si todas las consolas tienen `login local` respaldado por al menos un usuario con `secret`, AAA explícito local/local-case respaldado por ese usuario, o `password` + `login` sin AAA. FAIL si una consola reconocida no tiene autenticación o una lista AAA usa exclusivamente `none`. Sin consola, AAA externo, listas ausentes, sintaxis incompleta o contradictoria: NOT_EVALUATED. No se afirma NOT_APPLICABLE sin evidencia de plataforma que este contexto no proporciona. |
| IOS-ACL-001 | HIGH | ACL IPv4 extendidas nombradas y numeradas 100–199/2000–2699. FAIL ante `permit ip any any` inequívoco, incluyendo equivalentes `0.0.0.0 255.255.255.255`, secuencia opcional y sufijos log/log-input. PASS si hay entradas reconocidas sin ese permiso global. Sin ACL del alcance: NOT_APPLICABLE; ACL vacía, temporal, calificadores o sintaxis desconocidos: NOT_EVALUATED. |
| IOS-OSPF-001 | HIGH | Requiere proceso OSPFv2 válido y una interfaz con IPv4 estática primaria válida, `ip ospf <proceso> area <área>`, no shutdown y no pasiva. FAIL si falta autenticación o es `null`. PASS con autenticación simple o message-digest y su clave explícita sintácticamente reconocida. La autenticación de interfaz prevalece sobre la del área. Sin OSPF o solo interfaces pasivas/shutdown: NOT_APPLICABLE. Proceso aislado, network/virtual-link, VRF, clave ausente, DHCP, ambigüedad o key-chain: NOT_EVALUATED. |
| IOS-SNMP-001 | HIGH | Comunidades con modo RO/RW explícito, vista opcional y ACL opcional; sin modo ni argumentos adicionales se reconoce RO predeterminado documentado por Cisco. FAIL si el valor coincide con public/private sin distinguir mayúsculas (política preventiva) o el modo es RW. PASS si todas las comunidades reconocidas son RO y no predeterminadas en valor. Sin SNMP activo: NOT_APPLICABLE; SNMPv3 sin comunidades, sintaxis cifrada o desconocida: NOT_EVALUATED. |
| IOS-DOC-001 | LOW | FAIL sin hostname explícito o con Router/Switch, sin distinguir mayúsculas. PASS con un hostname explícito no genérico, incluidos nombres cortos. Directivas incompletas, múltiples o no reconocidas: NOT_EVALUATED. No se infieren identidades de conexión. |

Un FAIL demostrado prevalece sobre otras secciones ambiguas; PASS exige que
todas las secciones aplicables se resuelvan. Las directivas negadas no se
interpretan como mecanismos activos; `no ip ospf authentication` elimina la
excepción de interfaz y permite heredar la autenticación de área. Los errores
inesperados siguen siendo ERROR por el motor existente, no se ocultan.

Los controles de consola y OSPF comprueban **presencia de autenticación**, no
fortaleza criptográfica, validez de credenciales ni éxito de autenticación.
Aceptar password/tipo 7 o autenticación OSPF simple/MD5 no certifica su seguridad.
La ACL se evalúa sintácticamente, no según su aplicación, alcance o contadores.
RW siempre es incumplimiento de esta política, incluso con ACL restrictiva;
las necesidades excepcionales requieren revisión humana.

## Registro, evidencia y flujo integral

Orden de configuración: IOS-ADM-001, IOS-SRV-001, IOS-AUTH-001, IOS-ADM-002,
IOS-SRV-002, IOS-NTP-001, IOS-LOG-001, IOS-AUTH-002, IOS-ACL-001,
IOS-OSPF-001, IOS-SNMP-001, IOS-DOC-001. IOS-IF-001 permanece operacional.
Son 12 reglas de configuración y 13 evaluaciones integrales con el registro
habilitado, incluyendo estados no binarios. El agregado sigue siendo dinámico.

Los nuevos controles construyen evidencia sintética con fuente, hash y número
de línea cuando existe. No publican contraseñas, hashes de credenciales,
comunidades, claves OSPF, identificadores ACL, hostname ni IP de interfaces.
La vista de directivas respeta raíz/indentación y excluye comentarios y banners;
no pretende reemplazar un parser general de Cisco IOS.
Solo FAIL genera Finding, mediante el servicio existente.

El flujo integral reutiliza los servicios públicos sin cambios en SSH, collector,
API o lista blanca: cuatro evidencias, tres contextos operacionales y una sesión
mediante transporte simulado. No se ejecutó SSH real ni se tocó la CSR1000v.

## Fuentes técnicas

- [Cisco: autenticación AAA y login de líneas](https://www.cisco.com/en/US/docs/ios-xml/ios/sec_usr_aaa/configuration/15-2mt/sec-cfg-authentifcn.html).
- [Cisco: configuración de ACL IPv4](https://www.cisco.com/c/en/us/support/docs/security/ios-firewall/23602-confaccesslists.html).
- [Cisco: comandos OSPF, autenticación y precedencia](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_ospf/command/iro-cr-book/m_ospf-a1.html).
- [Cisco: configuración SNMP y comunidades RO/RW](https://www.cisco.com/c/en/us/support/docs/ip/simple-network-management-protocol-snmp/7282-12.html).
- [Cisco IOS: snmp-server community y acceso RO predeterminado](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/snmp/command/nm-snmp-cr-book/nm-snmp-cr-s2.html).
- [Cisco: referencia de hostname](https://www.cisco.com/c/en/us/td/docs/ios/fundamentals/command/reference/cf_book.pdf) y [valor Switch en Catalyst](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst3850/software/release/16-12/configuration_guide/sys_mgmt/b_1612_sys_mgmt_3850_cg/administering_the_device.html).

Las fuentes respaldan sintaxis y mecanismos; los umbrales y el subconjunto
evaluable son la política explícita de esta implementación, no certificación Cisco.

## Validación y resultados

Base histórica de esta rama antes de la expansión: **335 passed, 1 warning**.
Se incorporaron **153 pruebas nuevas** y se actualizaron expectativas de
integración que aún contaban siete/ocho evaluaciones. No se cambió la lógica
de las siete reglas previas ni sus fixtures históricas.

La suite final se ejecutó con `PYTHONUTF8=1` y el Python de `.venv`:
**488 passed, 1 warning in 6.50s**, salida real de `python -m pytest -q`.
El warning externo visible es `DeprecationWarning` de Starlette/AnyIO por
`anyio.abc.BlockingPortal`; no se ocultó ni se cambiaron dependencias.

| Control | Casos directos de contrato aprobados |
|---|---:|
| IOS-AUTH-002 | 24 |
| IOS-ACL-001 | 29 |
| IOS-OSPF-001 | 32 |
| IOS-SNMP-001 | 21 |
| IOS-DOC-001 | 13 |

A los 119 casos directos se suman 34 comprobaciones de metadatos, inmutabilidad,
errores sanitizados, comentarios/banners, múltiples interfaces OSPF,
deshabilitación, evidencia, no filtración a logs/consola y flujo integral.
Los tests nuevos bloquean `socket.connect` y `paramiko.SSHClient.connect`;
los flujos integrales usan fábricas simuladas, nunca el dispositivo real.
La respuesta pública conserva el hash `raw_output_sha256` y marcadores
redactados seguros, pero no salidas originales ni secretos.

Se corrigieron expectativas de test detectadas durante la revisión:
el hash/marcador redactado no son filtraciones; una fixture sin hostname
produce ahora un finding adicional legítimo; una comunidad con modo omitido
es RO por defecto según Cisco y no es una directiva incompleta. Los fallos
intermedios no se presentaron como aprobaciones ni motivaron alterar reglas previas.

Resultado real del comparador mediante `--summary-only` y `--scenario inseguro`:

| Escenario | Esperado = obtenido | PASS | FAIL | NOT_EVALUATED | Findings |
|---|---:|---:|---:|---:|---:|
| A: controlado | 12/12 | 12 | 0 | 0 | 0 |
| B: inseguro | 12/12 | 2 | 10 | 0 | 10 |
| C: insuficiente | 12/12 | 7 | 0 | 5 | 0 |
| Total calculado | 36/36 | 21 | 10 | 5 | 10 |

C omite versión SSH explícita, usa AAA externo, ACL temporal, OSPF mediante
network y SNMPv3 fuera del alcance. Las cinco reglas añadidas son PASS en A,
FAIL en B; en C son NOT_EVALUATED salvo IOS-DOC-001, que es PASS.
No hubo diferencias, estados ERROR, ni errores de contrato de orden/findings.
Cada escenario conserva el orden del registro y los findings corresponden
exactamente a FAIL. No se ejecutaron las consultas reales para obtener estos datos.

## Capturas recomendadas

Desde `C:\Users\Gamer\Desktop\grupo-1\Proyecto-Titulo-Cisco-IOS`, en PowerShell:

```powershell
$env:PYTHONUTF8 = '1'
```

1. `.\.venv\Scripts\python.exe scripts/evaluacion_2/run_validation_scenarios.py --summary-only`
   — resumen completo: 12 controles, 36/36 y 0 diferencias.
2. `.\.venv\Scripts\python.exe scripts/evaluacion_2/run_validation_scenarios.py --scenario inseguro`
   — tabla de 12 filas Esperado/Obtenido y correspondencia FAIL/findings.
3. `.\.venv\Scripts\python.exe -m pytest -q`
   — progreso, warning externo y resultado real final; no reutilizar una cifra antigua.
4. `.\.venv\Scripts\python.exe scripts/evaluacion_2/run_validation_scenarios.py --scenario no-evaluable`
   — cinco NOT_EVALUATED explícitos, demostrando que el motor no inventa PASS/FAIL.

La cuarta captura recomendada en este corte es offline; el wrapper real previo
sigue preparado pero no se ejecuta aquí. Una futura captura CSR1000v requiere
ejecución manual autorizada y debe distinguirse de estas pruebas sintéticas.
No mostrar configuraciones, otras ventanas con credenciales o datos del laboratorio.

## Límites y pendientes

No se audita completamente el router ni toda la sintaxis de Cisco IOS.
Quedan pendientes AAA externo, ACL con puertos/tiempos/objetos, OSPF activado
por network/VRF/key-chain y comprobación de vecinos, fortaleza de claves,
seguridad SNMPv3 y gestión de excepciones. NTP/Syslog siguen comprobando
presencia, no funcionamiento. VLAN/STP/trunk, PostgreSQL, IA y nuevos comandos
permanecen fuera del corte. La validación real y las capturas son manuales.

La Evaluación 2 amplía la evidencia de validación del prototipo; no implica el
cierre del proyecto. Todo queda sin commit y sin push para revisión.

## Correcciones posteriores a la auditoría final (Fase 1 histórica)

El 1 de octubre de 2026 se corrigieron tres defectos: una wildcard IPv4
255.255.255.255 equivale a cualquier dirección independientemente de la base;
OSPF no acepta una hostmask como netmask de interfaz; una comunidad SNMP
con sufijo incompleto RO ipv6 queda NOT_EVALUATED, sin revelar su valor.
Se añadieron cuatro regresiones (dos para wildcard, una para OSPF y una para
SNMP), conservando las comprobaciones de evidencia, sanitización y findings.
AGENTS.md se restauró exclusivamente a HEAD por solicitud del usuario.

Resultado real de esta fase: **492 passed, 1 warning in 6.96s**. El warning
externo Starlette/AnyIO permanece visible. Campaña existente: **36/36**,
21 PASS, 10 FAIL y 5 NOT_EVALUATED; cero diferencias y errores de contrato.
La cobertura sigue siendo 12 reglas running-config más IOS-IF-001: 13 integrales.

En esa fase la ampliación operacional posterior no se aplicó: la revisión automática de
permisos rechazó el parche de expansión del allowlist/contrato integral de cuatro
a ocho comandos. No quedaron cambios parciales de ese parche. Continúan
pendientes los nuevos comandos, parsers, reglas, fixtures e integración.
Ese bloqueo se resolvió después mediante autorización explícita: la implementación
y los resultados posteriores están en el registro operacional enlazado al inicio.
No se ejecutó SSH real, ni se modificó la CSR1000v. Sin commit y sin push.
