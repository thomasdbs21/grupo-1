# Evaluación 2: tres controles adicionales conservadores

Fecha: 1 de octubre de 2026. Corte inicial de implementación y validación OFFLINE;
la validación manual posterior reportada se distingue en su propia sección.
Previamente se completó la [auditoría 4→8](auditoria-migracion-evidencias-evaluacion-2.md)
con 607 pruebas aprobadas. No cambia la lógica de las 18 evaluaciones existentes.

## IOS-INT-001 — Interfaz no utilizada sin shutdown

Fuentes: running-config + show interfaces. MEDIUM. Recibe MultiSourceContext,
no un AnalysisContext aislado. Se correlaciona por nombre completo exacto único.
Subconjunto: Ethernet, FastEthernet, GigabitEthernet, TenGigabitEthernet,
TwentyFiveGigE, FortyGigabitEthernet, HundredGigE con número/puertos, sin subinterfaces.

- FAIL solamente con declaración exacta `description NETAUDIT_UNUSED`, `no shutdown`
  explícito, estado down/down y cuatro contadores (paquetes y errores de entrada
  y salida) presentes e iguales a cero. No se presume la habilitación por omisión.
- PASS para puertos correlacionados UP/UP o administratively down/down, sin
  contradicción con shutdown/no shutdown. No certifica un puerto seguro.
- NOT_APPLICABLE si solo hay tipos excluidos conocidos: Loopback, Tunnel, Vlan,
  Port-channel, BDI, Null, Virtual-Access, Virtual-Template y subinterfaces físicas.
- NOT_EVALUATED ante down/down sin declaración, contadores incompletos o actividad,
  fuente desconocida, nombres abreviados, tipo desconocido, interfaz ausente en
  una fuente, duplicados, contradicciones o estados no correlacionables.

El marcador es una declaración administrativa de política del prototipo,
NO un estándar Cisco ni una inferencia de inventario. Cero contadores por sí
solos tampoco demuestran abandono. La declaración puede estar desactualizada o
los contadores haberse reiniciado: el finding requiere revisión humana antes de
cualquier acción. No se agregan comandos ni se cambia configuración real.
Un FAIL demostrado prevalece sobre otra interfaz insuficiente; sin FAIL, una
interfaz insuficiente impide PASS agregado. Las excluidas no alteran el agregado.

Referencia de semántica operacional, no del marcador ni de un umbral de abandono:
[Cisco: estados y contadores de interfaces](https://www.cisco.com/c/en/us/support/docs/switches/catalyst-6500-series-switches/12027-53.html).

## IOS-AUTH-003 — Usuario local con password en vez de secret

Fuente: running-config global, HIGH. Sintaxis soportada:
`username <identidad> [privilege 0..15] password [0|7] <valor>` y
`username <identidad> [privilege 0..15] secret [0|5|8|9] <valor>`.
Identidad y valor son tokens únicos sin nombre entre comillas; no se imprimen.
Un token numérico sin payload es ambiguo, no prueba un mecanismo válido.

- FAIL: al menos una identidad evaluable tiene password reconocido.
- PASS: hay identidades evaluables y todas usan secret reconocido.
- NOT_APPLICABLE: no hay directivas globales username del alcance; comentarios,
  banners, formas `no username` y username de submodos no se confunden con usuarios.
- NOT_EVALUATED: sintaxis incompleta, opciones no soportadas (por ejemplo
  algorithm-type), tipos fuera del subconjunto, hijos inesperados o más de una
  directiva para LA MISMA identidad. Password + secret de esa identidad, en
  cualquier orden, no usa precedencia heurística; tampoco se deduplica en silencio.

Un FAIL inequívoco de otra identidad prevalece sobre una identidad ambigua.
No se afirma fortaleza criptográfica, identidad efectiva, protección de AAA ni
que todo secret sea moderno. CHAP puede necesitar mecanismos heredados: revisión
humana, nunca cambio automático. No revela usuario, password, hash ni tipo en evidencia.

Referencia consultada antes de fijar YAML/recomendación:
[Cisco IOS Security Command Reference: username y username secret](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/security/s1/sec-s1-cr-book/sec-cr-t2.html).

## IOS-ADM-003 — Timeout administrativo explícitamente deshabilitado

Fuente: running-config, MEDIUM. Alcance VTY numéricas y consola con un índice;
no AUX ni submodos de interfaz. `exec-timeout minutes [seconds]` con enteros
no negativos y una única directiva reconocida, sin rangos de líneas solapados.

- FAIL: `exec-timeout 0 0`; también `exec-timeout 0` por segundos opcionales omitidos.
- PASS: todas las líneas evaluables tienen timeout explícito reconocido no nulo.
  No se impone un límite inventado de 5/10 minutos; cualquier intervalo explícito
  no nulo satisface solo este control binario.
- NOT_APPLICABLE: no existen líneas del alcance.
- NOT_EVALUATED: directiva ausente, no/default exec-timeout, desconocida,
  incompleta, repetida/contradictoria o encabezados/rangos duplicados/solapados.

Cisco documenta 10 minutos predeterminados y 0 0 como timeout deshabilitado.
Se elige NE ante omisión para no certificar el valor efectivo de una plataforma
o entrada cuya configuración implícita no está en el contexto. Ausencia NUNCA
genera FAIL. Un 0 demostrado en otra sección evaluable prevalece sobre omisión;
solapamientos impiden afirmar una sección efectiva. Una excepción de laboratorio
se revisa manualmente; no cambia silenciosamente el estado técnico.

Referencia consultada antes del YAML:
[Cisco IOS Fundamentals: exec-timeout](https://www.cisco.com/c/en/us/td/docs/ios/fundamentals/command/reference/cf_book/cf_d1.html).

## Registro, evidencia y agregado

Registro estático: conserva los doce IDs anteriores y añade IOS-AUTH-003,
IOS-ADM-003 al final. Registro multifuente: reutiliza RuleRegistry para ID,
metadatos, orden y enabled; conserva los cinco controles anteriores y añade
IOS-INT-001 al final. IOS-IF-001 sigue con su cargador/contexto operacional.
Separación REAL: **14 de configuración + 7 operacionales/multifuente = 21**,
no 15 + 6. No se fuerza una regla multifuente a recibir configuración sola.
Dominio, servicio y DTO derivan cantidades de registros/colecciones, no del 21.

Evidencia nueva genérica y sanitizada: source/hash SHA-256 de evidencia (no hash
de un secreto), sin fragmentos de entrada, IP, nombres de interfaz/usuario,
destinos o configuración. Todas las evaluaciones se conservan; Finding exactamente
para cada FAIL, nunca para PASS/NA/NE/ERROR. Errores internos se mantienen ERROR,
sin texto sensible. Los ocho comandos y siete contextos no cambian en este corte.

## Resultados ejecutados en el corte OFFLINE inicial

Suite completa final: **703 passed, 1 warning in 7.52s** con Python de `.venv`
y PYTHONUTF8=1. Warning externo visible: alias anyio.abc.BlockingPortal deprecado
en starlette/testclient.py. Sin instalar o modificar dependencias.

Se añadieron 95 casos en test_evaluation2_additional.py, dos comprobaciones de
auditoría y un caso adicional del parámetro de error operacional existente.
Pruebas previas conservadas: actualizadas únicamente expectativas/IDs/orden
por las nuevas evaluaciones. La prueba de dos bloques de interfaces selecciona
sus dos bloques originales, pues las fixtures completas ahora incluyen otro puerto.
Se verifica además que los 18 estados previos no cambien en los tres escenarios.

Primera prueba dirigida: 92 passed y 2 failed por source_name omitido en el nuevo
test de errores internos; corregido el test, sin alterar regla. Primera suite de
integración: 691 passed y 9 failed por expectativas antiguas de IDs/conteos/sufijo;
se actualizaron manteniendo todas las aserciones. Comprobación dirigida posterior:
285 passed, 1 warning. Los fallos intermedios no se ocultan ni se relajan contratos.

| Fuentes SINTÉTICAS | Comparaciones correctas | PASS | FAIL | NOT_EVALUATED | Findings |
|---|---:|---:|---:|---:|---:|
| A: controlado | 21/21 | 21 | 0 | 0 | 0 |
| B: inseguro | 21/21 | 3 | 17 | 1 | 17 |
| C: insuficiente | 21/21 | 8 | 0 | 13 | 0 |

Campaña calculada: **63/63**, 0 diferencias, 32 PASS, 17 FAIL, 14 NOT_EVALUATED,
0 NOT_APPLICABLE, 0 ERROR, 0 errores de contrato. NA se comprueba en tests
unitarios, no se inventa en escenarios. Matrices por ID producidas por el script.

## Compatibilidad SSH del laboratorio y validación manual reportada

Fuente del resultado real: validación manual informada por el responsable del
laboratorio; no fue repetida por el agente durante este ajuste.

- **Problema:** Paramiko 5.0.0 no logró negociar KEX con CSR1000v IOS XE 16.9.5.
- **Diagnóstico reportado:** esa imagen del router ofrece únicamente
  `diffie-hellman-group-exchange-sha1` y `diffie-hellman-group14-sha1`.
  Paramiko 5.0.0 eliminó ambos algoritmos, según su
  [changelog oficial](https://www.paramiko.org/changelog.html).
- **Acción correctiva:** utilizar un entorno Python compatible con Paramiko 4.x;
  la conexión manual funcionó con 4.0.0. Se declara `paramiko>=4,<5` en
  `pyproject.toml`, sin cambiar el rango de Netmiko (`>=4.7,<5`). Paramiko ya era
  una dependencia transitiva; no se añade un paquete ajeno al transporte existente.
- **Resultado real reportado:** conexión exitosa y análisis integral read-only:
  una sesión SSH, una desconexión, 8/8 comandos canónicos, ocho evidencias,
  21 evaluaciones y tres findings. No se cambió la configuración del router.
- **Verificación offline reportada tras el cambio local:** 703 passed, un warning;
  campaña 63/63, cero diferencias y cero errores de contrato. La comprobación
  ejecutada durante este ajuste se registra por separado a continuación.

Entorno inspeccionado: Python 3.13.7, Netmiko 4.8.0 y Paramiko 4.0.0;
`pip check` sin requisitos incompatibles. Netmiko 4.8.0 admite `paramiko>=3.5.1`
sin límite superior en su dependencia base; por sí solo no evita Paramiko 5.x.
El límite explícito excluye 5.x al instalar este proyecto con sus dependencias.
No se reinstalaron paquetes ni se creó un entorno limpio durante este ajuste.

Esta excepción responde al laboratorio heredado validado; no recomienda KEX
SHA-1 para producción ni supone que NetAudit modifique el dispositivo. No se
certifican todas las versiones 4.x ni se fija toda la resolución transitiva.
Revisar la restricción y las actualizaciones de seguridad cuando se apruebe
actualizar el laboratorio y repetir su validación con transporte moderno.
No se guardan host/IP, usuarios, contraseñas, claves ni running-config reales.

### Comprobación OFFLINE del ajuste de compatibilidad

Ejecutada con el mismo `.venv`, Paramiko 4.0.0 y `PYTHONUTF8=1`:

- `python -m pytest -q`: **703 passed, 1 warning in 7.46s**. Se conserva visible
  el warning externo de Starlette/AnyIO indicado en el corte inicial.
- `python scripts/evaluacion_2/run_validation_scenarios.py --summary-only`:
  **63/63**, cero diferencias, 32 PASS, 17 FAIL, 14 NOT_EVALUATED,
  cero NOT_APPLICABLE, cero ERROR y cero errores de contrato.
- Validación programática de requisitos: versión instalada admitida por el
  proyecto y Netmiko; rango 4.x permitido y 5.x excluido. Ambos KEX requeridos
  están disponibles localmente, sin crear un transporte ni abrir SSH.
- `git diff --check`: sin errores de whitespace; los avisos LF→CRLF son
  advertencias de normalización de Git, no fallos de pruebas.

No se alteraron reglas, parsers, collector, scripts, pruebas ni fixtures durante
este ajuste. No se instalaron paquetes, no se abrió SSH y no se hizo commit/push.

## Máximo cuatro capturas posteriores

PowerShell desde `C:\Users\Gamer\Desktop\grupo-1\Proyecto-Titulo-Cisco-IOS`:

~~~powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts/evaluacion_2/run_validation_scenarios.py --summary-only
.\.venv\Scripts\python.exe scripts/evaluacion_2/run_validation_scenarios.py --scenario inseguro
.\.venv\Scripts\python.exe -m pytest -q
~~~

Una captura por comando: resumen completo con FUENTES SINTÉTICAS; tabla completa
Esperado/Obtenido/OK del escenario B; progreso, warning y línea final real de pytest.
Ocultar otras ventanas, credenciales, variables sensibles y configuraciones.

Cuarta captura, **solo en futura ejecución manual expresamente autorizada**:

~~~powershell
.\.venv\Scripts\python.exe scripts/evaluacion_2/run_csr1000v_validation.py
~~~

Usuario introduce host/puerto/usuario/contraseña de forma oculta. Mostrar solo
bloque final sanitizado (sesiones/consultas/evidencias/evaluaciones/IDs/estados/
severidades). No mostrar configuración ni salidas originales/normalizadas,
direcciones de dispositivo/interfaces/destinos, nombres reales o secretos.
Ocho consultas del collector en una sola sesión; preparación interna de terminal
de Netmiko no se contabiliza como consulta. No reintento automático.

## Límites y pendiente

La compatibilidad real ampliada fue reportada por el responsable para esa imagen
con Paramiko 4.0.0; no se repitió SSH durante este ajuste. Un marcador desactualizado
no demuestra abandono; IOS-INT-001 es una política acotada de sin uso declarado.
No hay cobertura exhaustiva de Cisco IOS, inventario de vecinos OSPF esperado,
deltas temporales ni soporte de toda variante de CLI. IA NO integrada y PostgreSQL/
persistencia NO implementados. AGENTS no modificado. Sin commit/push/SSH real ni
configuración de dispositivos; resultados quedan para revisión.

“La Evaluación 2 amplía la evidencia de validación del prototipo; no implica el cierre del proyecto.”
