# Escenarios sintéticos de la Evaluación 2

Fixtures independientes para comparar expectativas con el servicio público
`analyze_file()` para configuración y el servicio integral para ocho evidencias.
No son configuraciones para aplicar a un equipo y no prueban
la validez completa de una configuración IOS.

| Escenario | Archivo | Control probado | Expectativa |
|---|---|---|---|
| A | [escenario_seguro.cfg](escenario_seguro.cfg) | Controles anteriores, usuario local secret y timeout explícito no nulo | 14 PASS |
| B | [escenario_inseguro.cfg](escenario_inseguro.cfg) | Controles inseguros anteriores, usuario local password y timeout deshabilitado | 12 FAIL y 2 PASS |
| C | [escenario_no_evaluable.cfg](escenario_no_evaluable.cfg) | Insuficiencia anterior, sintaxis de usuario fuera del subconjunto y timeout ausente | 7 PASS y 7 NOT_EVALUATED |

Los valores `<REDACTED>` son marcadores sin credenciales. Los destinos
`192.0.2.10` y `192.0.2.20` son ficticios, del bloque reservado para
documentación; no representan el laboratorio. Las salidas del comparador
muestran solo IDs, estados y verificaciones.

C no representa un archivo truncado: falta deliberadamente información
o sintaxis soportada para concluir sobre siete controles estáticos. NTP y Syslog se mantienen
presentes en todos los escenarios para aislar los controles de administración.

Las catorce reglas de configuración se ejecutan en el orden vigente del registro.
Las siete reglas operacionales/multifuente necesitan las fixtures de
[operacional](operacional/README.md); el script principal las incorpora por defecto.
La ausencia de findings en A o C no equivale a certificar un dispositivo seguro.

Las expectativas están declaradas por regla en
[run_validation_scenarios.py](../../scripts/evaluacion_2/run_validation_scenarios.py).
El script devuelve código 1 ante diferencias de estado, orden o correspondencia
de findings y no abre SSH.

## Campaña integral actual

Las salidas SHOW de `operacional/` son explícitamente SINTÉTICAS, no capturas
ni evidencia recopilada de CSR1000v. Las expectativas integrales añaden:

| Escenario | Evaluaciones | PASS | FAIL | NOT_EVALUATED | Findings |
|---|---:|---:|---:|---:|---:|
| A | 21 | 21 | 0 | 0 | 0 |
| B | 21 | 3 | 17 | 1 | 17 |
| C | 21 | 8 | 0 | 13 | 0 |

B incluye un vecino transitorio: no demuestra expectativa persistente y queda
NOT_EVALUATED. C añade fuentes operacionales desconocidas/correlación ausente.
La campaña compara 63 estados, sin afirmar resultados reales del laboratorio.
A incluye un puerto declarado sin uso administrativamente deshabilitado;
B lo mantiene explícitamente habilitado, down/down y sin paquetes/errores.
description NETAUDIT_UNUSED es una declaración de política en la fixture,
no una inferencia de abandono basada solo en el estado del enlace.
