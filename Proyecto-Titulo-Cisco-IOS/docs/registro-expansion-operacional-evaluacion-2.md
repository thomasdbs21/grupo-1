# Expansión operacional para la Evaluación 2

Registro histórico del primer corte operacional: 18 evaluaciones y 605 pruebas.
La [auditoría 4→8](auditoria-migracion-evidencias-evaluacion-2.md) y los
[tres controles posteriores](registro-controles-adicionales-evaluacion-2.md)
describen el estado vigente. Las cifras y capturas propuestas abajo corresponden
a este primer corte, no a una nueva validación real.

## Decisión aprobada y contratos

Autorización explícita del 1 de octubre de 2026: ocho comandos en orden canónico:
show running-config, show version, show ip interface brief, show ip ssh,
show interfaces, show access-lists, show ntp associations, show ip ospf neighbor.
Implementación y pruebas exclusivamente OFFLINE, sin SSH real, commit ni push.
SHOW exactos, sin pipes/argumentos arbitrarios ni operaciones de configuración.
Una sesión, validación previa del allowlist, desconexión, UUID común, UTC y
SHA-256 del original. AGENTS.md queda restaurado a HEAD por solicitud; su
contrato de cuatro comandos describe el corte histórico, sustituido aquí.

TextFSM propio y modelos inmutables mínimos. Formato desconocido/incompleto
no equivale a lista vacía. Direcciones NTP y IDs/direcciones de vecinos se
descartan en los modelos nuevos; nombres de ACL/interfaz quedan internos para
correlación, no en evidencia pública. No se cambia lógica de reglas anteriores.

| ID | Severidad | Contrato |
|---|---|---|
| IOS-INT-002 | LOW | UP/UP en brief, sección de interfaz única y nombre completo exacto: PASS con description no vacía; FAIL sin ella. Sin UP/UP: NOT_APPLICABLE. Correlación ausente/ambigua: NOT_EVALUATED. |
| IOS-ACL-002 | MEDIUM | ACL IPv4 standard/extended concordantes entre config y show: PASS con ip access-group in/out de interfaz; FAIL sin aplicación reconocida. Sin ACL: NOT_APPLICABLE. Discrepancia o aplicaciones alternativas/ambiguas: NOT_EVALUATED. No usa hits como indicador de aplicación. |
| IOS-NTP-002 | MEDIUM | PASS con * sys.peer, stratum <16 y reach >0; FAIL con asociaciones evaluables sin sincronización. Tabla reconocida vacía: NOT_APPLICABLE; desconocida/incompleta: NOT_EVALUATED. |
| IOS-AVL-001 | MEDIUM | UP/UP; por dirección, errors/(packets+errors). FAIL si supera 1%, con al menos 10.000 observaciones y 100 errores. PASS si ambas direcciones tienen muestra suficiente y están bajo el umbral. Muestra insuficiente: NOT_EVALUATED; ninguna UP/UP: NOT_APPLICABLE. |
| IOS-OSPF-002 | HIGH | PASS limitado a vecinos observados FULL o 2WAY/DROTHER. Sin proceso OSPFv2 ni vecinos: NOT_APPLICABLE. Estados transitorios, tabla vacía con OSPF o expectativa no demostrable: NOT_EVALUATED. No emite FAIL en este corte. |

El umbral AVL es una política de alerta histórica del prototipo, no una norma
Cisco ni tasa temporal. Muestra/errores mínimos evitan clasificar un error
aislado como HIGH. Se adopta MEDIUM en lugar del HIGH preliminar del catálogo:
una fotografía acumulada no acredita degradación actual ni impacto crítico.
No existe WARN en RuleStatus, ni se agrega un estado nuevo.

OSPF no recibe un FAIL artificial: no hay inventario de vecinos esperados ni
observación temporal. 2WAY puede ser normal entre DROTHER; PASS no certifica
la totalidad de las adyacencias esperadas. Pruebas cubrirán explícitamente que
ausencia y transitorios no generan findings sin una expectativa segura.

## Referencias y límites

- [Cisco: contadores de interfaces](https://www.cisco.com/c/en/us/support/docs/switches/catalyst-6500-series-switches/12027-53.html).
- [Cisco: NTP y sys.peer](https://www.cisco.com/c/en/us/td/docs/routers/asr920/configuration/guide/timing/17-1-1/b-timing-sync-xe-17-1-asr920/m_bsm-ntp-asr920.html).
- [Cisco: estados de vecinos OSPF](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_ospf/command/iro-cr-book/ospf-s1.html).
- [Cisco: 2WAY normal en multiacceso](https://www.cisco.com/c/en/us/support/docs/ip/open-shortest-path-first-ospf/13683-11.html).

No cubre todo Cisco IOS/IOS XE. Fixtures explícitamente sintéticas, nunca
evidencia real CSR1000v. No se implementan IA, persistencia ni cambios automáticos.
La Evaluación 2 amplía la evidencia de validación del prototipo; no implica el
cierre del proyecto. Los resultados reales de este corte están a continuación.

## Resultados reales del primer corte (históricos)

Suite completa final con PYTHONUTF8=1 y Python de `.venv`: **605 passed, 1 warning
in 17.74s**. Warning externo visible de Starlette/AnyIO: alias
`anyio.abc.BlockingPortal` deprecado. Sin cambios de dependencias.
La fase correctiva previa obtuvo 492 passed; esta ampliación añade 105 casos
en test_operational_expansion.py y ocho casos por ampliar parametrizaciones
del batch y fallos de cada comando. No se eliminan tests anteriores.
La última regresión evita declarar una ACL sin aplicación cuando una directiva
no soportada referencia su identificador, incluso antes de su definición.
La coincidencia de identificadores, especialmente numéricos, puede generar
NOT_EVALUATED conservador; no se interpreta como una aplicación demostrada.

La primera integración obtuvo 579 passed y 1 failed por una posición antigua
de la regla sintética futura: se actualizó la posición y se añadió el orden
exacto de las seis operacionales; no se relajó la comprobación ni se alteró
la regla para satisfacer el test. La comprobación dirigida posterior obtuvo
134 passed, 1 warning antes de la suite final.

Cobertura de este corte: **12 reglas running-config + 6 operacionales/multifuente = 18**.
Registro operacional: IOS-IF-001, IOS-INT-002, IOS-ACL-002, IOS-NTP-002,
IOS-AVL-001, IOS-OSPF-002. La última conserva una detección limitada, sin FAIL
de vecino esperado mientras no exista inventario/topología suficiente.
Dominio y agregado no fijan el total; una prueba reduce el registro operacional
y verifica que la cantidad resultante cambia sin modificar el dominio.

Campaña integral: **3 escenarios, 18 reglas por escenario, 54/54 coincidencias,
0 diferencias, 0 ERROR y 0 errores de contrato**. Totales calculados:
29 PASS, 14 FAIL, 11 NOT_EVALUATED, 0 NOT_APPLICABLE.

| Escenario sintético | Esperado = obtenido | PASS | FAIL | NOT_EVALUATED | Findings |
|---|---:|---:|---:|---:|---:|
| A: controlado | 18/18 | 18 | 0 | 0 | 0 |
| B: inseguro | 18/18 | 3 | 14 | 1 | 14 |
| C: insuficiente | 18/18 | 8 | 0 | 10 | 0 |

Se verificaron parsers de las cuatro fuentes, formato desconocido/incompleto,
colecciones inmutables, metadatos, límites numéricos, correlación, sanitización,
ocho comandos exactos en orden, una fábrica de conexión simulada y desconexión,
ausencia de enable/config_mode/send_config_set y Finding exclusivamente desde FAIL.
El lote antiguo de cuatro evidencias ya no constituye un análisis integral válido.
La API mantiene sus rutas y payloads; cardinalidad y comandos tipados pasan a ocho.
Esta modificación de contrato requiere adaptar consumidores del lote anterior.

AGENTS.md coincide con HEAD. No se modificaron reglas previas salvo las tres
correcciones aprobadas, ni dependencias, persistencia o dispositivos.
Los archivos nuevos permanecen sin seguimiento y los cambios anteriores sin commit;
git diff --stat no incluye archivos sin seguimiento. No se hizo staging adicional.

## Cuatro capturas propuestas en ese corte (históricas)

Directorio PowerShell: `C:\Users\Gamer\Desktop\grupo-1\Proyecto-Titulo-Cisco-IOS`.
Primero `$env:PYTHONUTF8 = '1'`.

1. `.\.venv\Scripts\python.exe scripts/evaluacion_2/run_validation_scenarios.py --summary-only`
   — mostrar resumen completo: 18 controles, 54/54, cero diferencias.
2. `.\.venv\Scripts\python.exe scripts/evaluacion_2/run_validation_scenarios.py --scenario inseguro`
   — mostrar tabla Esperado/Obtenido, 14 FAIL y OSPF NOT_EVALUATED; conservar
   visible la etiqueta FUENTES SINTÉTICAS.
3. `.\.venv\Scripts\python.exe -m pytest -q`
   — mostrar progreso, warning externo y número REAL del momento, no reutilizar
   automáticamente el resultado de este registro.
4. **Pendiente de autorización para la ejecución real manual**:
   `.\.venv\Scripts\python.exe scripts/evaluacion_2/run_csr1000v_validation.py`
   — el usuario introduce host, puerto, usuario y contraseña de forma oculta.
   Mostrar solo ocho consultas auditadas, evidencias, IDs, estados y severidades;
   no configuraciones, destinos, interfaces, credenciales ni otras ventanas sensibles.
   Una sola sesión/intento, sin reintentos automáticos. No se ejecutó aquí.

Los ocho comandos son consultas del collector; no se contabilizan como consultas
los intercambios internos de preparación de terminal de Netmiko. La compatibilidad
real de las plantillas con la salida de CSR1000v no queda demostrada por fixtures.
Siguen pendientes validación real, inventario de vecinos esperados, variantes CLI,
deltas de contadores, otras aplicaciones ACL y aprobación docente de políticas.
