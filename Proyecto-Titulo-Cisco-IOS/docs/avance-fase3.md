# Avance técnico del 10 de noviembre

## Selección previa a la implementación

El corte inicial de main es 74e66c0. El registro contiene 14 reglas de archivo y el análisis integral incorpora otras siete operacionales. La suite ordinaria obtuvo 815 passed y un warning de deprecación de Starlette/AnyIO en 15,34 s.

| ID propuesto | Evidencia en running-config | Justificación del perfil corporativo |
| --- | --- | --- |
| IOS-SRV-003 | ip finger o service finger | Finger puede divulgar información de sesiones. Revisar su activación explícita. |
| IOS-SRV-004 | service pad | PAD sirve a redes X.25. Su habilitación merece revisión en una red sin ese requisito. |
| IOS-IP-002 | ip source-route | La configuración permite procesar opciones de encaminamiento indicadas por el origen. Revisar la política de encaminamiento IPv4. |

Las 21 reglas anteriores cubren VTY, consola, autenticación, HTTP, pequeños servidores, NTP, Syslog, ACL, OSPF, SNMP, documentación y estado de interfaces. Ninguna decide el estado explícito de estas tres directivas. Se descartó BOOTP porque la semántica cambia según versión y servicio DHCP. Tampoco se propone juzgar QoS sin conocer la política de tráfico del cliente.

Se evalúa una política de endurecimiento que requiere deshabilitar estas funciones. FAIL describe una directiva habilitada, no demuestra accesibilidad desde la red ni explotación. Una excepción operativa requiere revisión humana. La ausencia no prueba un valor por defecto. [Guía de endurecimiento Cisco IOS XE](https://sec.cloudapps.cisco.com/security/center/resources/IOS_XE_hardening).

## Ensayo reproducible de cuatro minutos

| Tiempo | Integrante | Acción y evidencia |
|---|---|---|
| 0:00–0:30 | Emilio | Presentar el origen Archivo y el propósito del perfil corporativo. |
| 0:30–1:15 | Thomas | Cargar [demo_servicios.cfg](../samples/fase_3/demo_servicios.cfg) y pulsar Analizar. Se esperan 17 evaluaciones y tres Findings nuevos. |
| 1:15–2:15 | Maikol | Abrir Finger, PAD y source routing en Hallazgos. Comparar ID, severidad, línea y recomendación con el archivo. |
| 2:15–3:15 | Axl | Mostrar el registro y la condición de FAIL en explicit_services.py. Explicar por qué una directiva omitida se conserva como NOT_EVALUATED. |
| 3:15–4:00 | Thomas | Exportar los hallazgos y volver al resumen. La explicación es opcional; utilizarla solo si una prueba actual produjo una respuesta válida. |

## Pruebas y planificación

La suite completa pasó de 815 a 852 pruebas aprobadas. Ambas ejecuciones mostraron un warning de deprecación de Starlette/AnyIO y cero fallos finales. La campaña offline ejecutó tres lotes con ocho evidencias cada uno. Sus 72 evaluaciones coincidieron con las expectativas: 32 PASS, 17 FAIL y 23 NOT_EVALUATED. Las tres directivas nuevas no aparecen en esos archivos históricos, por lo que cada caso conserva tres resultados indeterminados adicionales. El archivo dedicado demuestra los tres FAIL con evidencia explícita.

Para reproducir desde el proyecto: `python -m pytest -q` y `python scripts/evaluacion_2/run_validation_scenarios.py --summary-only`. La validación ordinaria cubre FastAPI, la UI, las exportaciones y errores controlados de IA con dobles de prueba. No se midió cobertura ni se ejecutó SSH o inferencia en vivo para este incremento.

La meta del 10 era entregar aproximadamente tres reglas reproducibles. Se incorporaron tres. El video y los resultados de la exposición aún requieren ejecución. No se estimaron porcentajes de avance global ni desviaciones en horas sin una línea base fechada. El equipo revisará en el ensayo si la demo cabe en el tiempo asignado.
