# Registro de preparación de la Evaluación 2: validación

**Preparación:** 1 de octubre de 2026. **Evaluación prevista:** 6 de octubre de 2026.

Este registro conserva los resultados históricos de la campaña inicial
(335 pruebas y siete controles por escenario). La expansión estática posterior
a doce controles está en el [registro de expansión](registro-expansion-reglas-evaluacion-2.md).
El primer corte operacional tuvo dieciocho controles y ocho evidencias sintéticas.
La campaña vigente tiene veintiún controles; sus contratos y resultados están en
el [registro actual](registro-controles-adicionales-evaluacion-2.md).

## Objetivo y aporte

Ampliar la evidencia reproducible de pruebas y validación, comparando
**prueba realizada → resultado esperado → resultado obtenido**.
La exposición anterior presentó arquitectura, tecnologías, ocho reglas y
resultados históricos. Esta campaña contrasta tres entradas controladas con
el motor vigente y ejecuta la suite actual.

Se relaciona con la actividad «Pruebas y validación» de la Carta Gantt,
páginas 5–6 de la
[definición APT](../../Entregables-APT/Fase-1/Grupales/Grupo-1_Definicion_Proyecto_APT_Fase-1.pdf),
y con el seguimiento de [Fase 2](../../Avances-del-Proyecto/Fase-2.md).
En la preparación inicial no se agregaron reglas ni se alteró el motor,
el collector o los endpoints. El corte estático posterior añadió cinco reglas
sin cambios en el collector; luego se autorizó explícitamente la ampliación
operacional a ocho comandos, sin cambiar rutas ni payloads de conexión.

## Escenarios y matriz de la campaña inicial (histórica)

Las [tres fixtures](../samples/evaluacion_2/README.md) son independientes,
sintéticas y no deben aplicarse a dispositivos. A configura los controles
soportados; B habilita cinco condiciones inseguras; C omite la versión SSH
explícita y conserva los otros controles. NTP/Syslog están presentes en los tres.

Cada celda indica **esperado → obtenido**, según ejecución local real del
[comparador](../scripts/evaluacion_2/run_validation_scenarios.py).

| Regla | A: seguro | B: inseguro | C: información insuficiente |
|---|---|---|---|
| IOS-ADM-001 | PASS → PASS | FAIL → FAIL | PASS → PASS |
| IOS-SRV-001 | PASS → PASS | FAIL → FAIL | PASS → PASS |
| IOS-AUTH-001 | PASS → PASS | FAIL → FAIL | PASS → PASS |
| IOS-ADM-002 | PASS → PASS | FAIL → FAIL | NOT_EVALUATED → NOT_EVALUATED |
| IOS-SRV-002 | PASS → PASS | FAIL → FAIL | PASS → PASS |
| IOS-NTP-001 | PASS → PASS | PASS → PASS | PASS → PASS |
| IOS-LOG-001 | PASS → PASS | PASS → PASS | PASS → PASS |

Resultado histórico calculado: **3 escenarios, 7 reglas por escenario, 21 comparaciones,
21 coincidencias, 0 diferencias; 15 PASS, 5 FAIL y 1 NOT_EVALUATED verificados**.
Orden e IDs correctos; findings derivados exactamente de FAIL.
A y C producen 0 findings; B produce 5.

## Pruebas ejecutadas en la preparación inicial

- Nuevas pruebas dirigidas: `21 passed in 1.86s`.
- Primera suite con `python -X utf8 -m pytest -q`: `334 passed, 1 failed,
  2 warnings in 7.34s`. La prueba existente de CLI falló por una diferencia
  de codificación entre pytest en UTF-8 y su subproceso con codificación Windows.
- Comprobación dirigida con `PYTHONUTF8=1`: `1 passed in 3.29s`.
- Suite completa con UTF-8 heredable: **`335 passed, 1 warning in 6.58s`**.

El warning restante es externo: `DeprecationWarning` en
`starlette/testclient.py`, por el alias `anyio.abc.BlockingPortal`.
No se ocultó ni se modificaron dependencias o pruebas históricas.

Las 21 pruebas nuevas comprueban escenarios, expectativas, cálculos, diferencias,
formato, importación sin efectos, protección de entrada, errores sanitizados y
una sesión con los cuatro comandos usando un transporte simulado. Bloquean
conexiones de socket y SSH; no acceden a la CSR1000v.

## Validación real preparada

El wrapper inicial reutilizó `collect_and_analyze_device()` con los cuatro
comandos del contrato histórico. El [wrapper manual vigente](../scripts/evaluacion_2/run_csr1000v_validation.py)
utiliza los ocho comandos aprobados: `show running-config`, `show version`,
`show ip interface brief`, `show ip ssh`, `show interfaces`, `show access-lists`,
`show ntp associations` y `show ip ospf neighbor`.
Solicita host, puerto, usuario y contraseña de forma oculta,
usa una única sesión, cuenta consultas y desconexión y no reintenta.

Imprime solo plataforma genérica, contadores, IDs, estados y severidades
del catálogo. No escribe credenciales, configuraciones ni evidencias en archivos.
La severidad de una regla PASS no representa un finding.

**No se ejecutó una validación SSH real durante esta preparación.**
Posteriormente, el responsable informó una validación manual real con Paramiko
4.0.0: una sesión, una desconexión, ocho comandos, ocho evidencias, 21 evaluaciones
y tres findings. El fallo de KEX con Paramiko 5.0.0 y su resolución en el entorno
Python se registran en el [registro actual](registro-controles-adicionales-evaluacion-2.md#compatibilidad-ssh-del-laboratorio-y-validación-manual-reportada).
Ese resultado reportado no se sustituye por simulación ni se verificó repitiendo
SSH durante el ajuste de dependencias. Netmiko puede efectuar preparación interna de terminal al conectar;
el contador vigente audita las ocho consultas enviadas por el collector, no todos los
mensajes internos del protocolo.

## Cuatro capturas

Usar PowerShell, desde
`C:\Users\Gamer\Desktop\grupo-1\Proyecto-Titulo-Cisco-IOS`.
Preparar UTF-8 heredable una sola vez:

~~~powershell
$env:PYTHONUTF8 = '1'
~~~

| Captura | Comando | Parte visible |
|---|---|---|
| 1 | `.\.venv\Scripts\python.exe scripts\evaluacion_2\run_validation_scenarios.py --summary-only` | Resumen vigente calculado, estados y resultado; etiqueta FUENTES SINTÉTICAS |
| 2 | `.\.venv\Scripts\python.exe scripts\evaluacion_2\run_validation_scenarios.py --scenario inseguro` | Tabla Esperado/Obtenido vigente, todas las verificaciones y etiqueta FUENTES SINTÉTICAS |
| 3 | `.\.venv\Scripts\python.exe -m pytest -q` | Progreso, warning externo y línea final real |
| 4 | `.\.venv\Scripts\python.exe scripts\evaluacion_2\run_csr1000v_validation.py` | Solo el bloque final sanitizado, posterior a las entradas ocultas |

No mostrar otras ventanas, historial de credenciales, IP/hostname reales,
archivos de configuración, variables sensibles ni salidas completas de comandos.
No usar parámetros de conexión visibles en la línea de comandos.
Si la validación real falla, conservar el error sanitizado como resultado;
no presentarlo como éxito.

## Limitaciones y pendiente

La campaña inicial validó siete controles; la vigente incluye configuración y
fuentes operacionales sintéticas según el registro operacional, no la seguridad
completa ni todas las variantes IOS. IOS-NTP-001/IOS-LOG-001 comprueban presencia
de configuración; IOS-NTP-002 comprueba sincronización observada. Ninguna regla
certifica recepción efectiva de Syslog. IOS-IF-001 se ejercita offline y el
responsable informó una validación integral manual posterior de 21 evaluaciones.
El resultado de un laboratorio no certifica todas las variantes IOS o versiones 4.x.
El acceso real requiere laboratorio autorizado, terminal interactiva y permisos
para los ocho comandos. Si `getpass` no puede ocultar entradas, el wrapper aborta.
Quedan pendientes las capturas finales y su revisión académica; cualquier nueva
ejecución SSH requiere autorización y no forma parte del ajuste de compatibilidad.
No se implementan PostgreSQL, IA ni PowerPoint.

“La Evaluación 2 amplía la evidencia de validación del prototipo; no implica el cierre del proyecto.”
