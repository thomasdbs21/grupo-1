# Fixtures operacionales SINTÉTICAS

Estas salidas se construyeron para probar contratos y comparación esperado/obtenido.
No fueron recopiladas de CSR1000v ni acreditan su estado. Nunca se deben presentar
como captura real. Direcciones pertenecen a rangos de documentación.

A: UP/UP descrita, ACL aplicada, sys.peer NTP, contadores bajo umbral y FULL OSPF.
B: UP/UP sin descripción, ACL sin aplicación, NTP no sincronizado, errores
históricos sobre umbral y vecino transitorio (NOT_EVALUATED, nunca FAIL inventado).
C: interfaz sin correlación y salidas nuevas deliberadamente desconocidas;
conserva estados NOT_EVALUATED en vez de inventar cumplimiento/incumplimiento.

El script público analiza ocho CommandEvidence en memoria, sin transporte SSH.

El corte adicional incorpora un segundo puerto físico en A y B: ambos declaran
description NETAUDIT_UNUSED. A lo presenta administratively down con shutdown;
B, down/down, cuatro contadores cero y no shutdown explícito. La declaración
es una política sintética acotada, no una semántica universal de Cisco IOS.
