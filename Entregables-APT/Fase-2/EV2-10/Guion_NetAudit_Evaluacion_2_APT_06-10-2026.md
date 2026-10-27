# Guion oral NetAudit Evaluación 2 APT

Martes 6 de octubre de 2026. Duración objetivo: 3 a 4 minutos, incluida la demostración breve. Las notas del PowerPoint contienen el contexto técnico y las precauciones.

## Slide 1 Tareas técnicas y estado de avance

Tiempo: 45–60 segundos.

“En esta evaluación mostramos el avance de NetAudit frente a nuestra Carta Gantt. El foco es conectividad y redes: obtener evidencia Cisco y producir diagnósticos repetibles, sin modificar el dispositivo.

Alcance, arquitectura, recolección, motor y API están completados para el alcance actual. Tenemos 21 controles deterministas y ocho comandos autorizados. Esto no significa que todo el proyecto ni toda la cobertura de Cisco IOS estén terminados.

Pruebas y validación se estima en 65% de la actividad completa. Ya contamos con pruebas automatizadas, escenarios reproducibles y validación real, pero falta la validación final integrada.

Estamos en semana 8, en transición a la 9. Interfaz y reportes comienza en S10, por lo que está planificada y aún no iniciada, sin retraso. La siguiente etapa abordará esa capa, junto con el asistente explicativo. El cierre final todavía está pendiente.”

### Aclaraciones de planificación

- El 65% es una estimación conservadora de avance de la actividad completa. No procede de una fórmula sobre 703 tests o 63 comparaciones y no representa un porcentaje de cobertura.
- Los dos 100% calificados corresponden al catálogo actual/MVP y a la API actual, no a interfaz, persistencia, IA ni al proyecto completo.
- La Gantt reducida conserva exactamente los ocho tramos de la matriz original de Fase 1, página 6: S1–S2, S2–S4, S5–S7, S6–S10, S9–S12, S10–S13, S11–S15 y S14–S18. No modifica la planificación.
- El equipo confirmó el avance académico en S8, en transición a S9. Interfaz y reportes está planificada para S10–S13 y no está atrasada. La API actual y la validación ya ejecutada incluyen trabajo anticipado respecto a S9–S12 y S11–S15.
- El PDF original no contiene la fecha de inicio de S1. La línea asociada al corte EV2 representa aproximadamente la transición S8/S9 informada por el equipo. No asigna fechas calendario a cada semana. Las fechas comprometidas siguen expresadas en semanas originales.

## Slide 2 Entregables y criterios de éxito

Tiempo: 45–60 segundos.

“Los entregables tienen criterios verificables. La recolección debe usar una sesión, ocho comandos autorizados y una desconexión correcta. El motor conserva todas las evaluaciones y genera findings únicamente desde FAIL.

La validación de software obtuvo 703 pruebas aprobadas. La campaña sintética obtuvo 63 coincidencias de 63 comparaciones. Son pruebas distintas de la validación real del router.

El obstáculo real fue la negociación SSH: Paramiko 5 no aceptó los KEX heredados ofrecidos por IOS XE 16.9.5. Corregimos el entorno Python a Paramiko 4.x, con 4.0.0 validado. NetAudit no cambió el router.

Esta compatibilidad se limita al laboratorio legacy; no recomienda SHA-1 para producción. La IA no está implementada: en Evaluación 3 explicará findings que las reglas ya hayan validado.”

### Datos de apoyo si preguntan

- Error reportado previo a autenticación: `Incompatible ssh peer (no acceptable kex algorithm)`.
- KEX ofrecidos: `diffie-hellman-group-exchange-sha1` y `diffie-hellman-group14-sha1`.
- Restricción del proyecto: `paramiko>=4,<5`. Netmiko mantiene `>=4.7,<5`.
- Los cuatro comandos adicionales aportan información de interfaces, ACL, asociaciones NTP y vecinos OSPF. No se aceptan comandos arbitrarios.
- IA y PostgreSQL/persistencia no implementados. Interfaz y reportes funcionales pendientes.

## Slide 3 Laboratorio y evidencias

Tiempo total, incluida demo: 90–120 segundos.

“Netmiko obtiene información por SSH de solo lectura. CommandEvidence conserva el comando, la fecha y SHA-256 para verificar integridad. CiscoConfParse y TextFSM estructuran las entradas. Los contextos inmutables llegan a reglas deterministas. Solo FAIL genera un Finding.

La captura real demuestra una sesión, una desconexión, ocho comandos y ocho evidencias. El motor obtuvo 21 evaluaciones y tres findings: NTP, Syslog y el uso de password en un usuario local. No mostramos identidades ni valores sensibles.

Por separado, tres escenarios sintéticos produjeron 63 coincidencias sin diferencias ni errores de contrato. Las 703 pruebas son tests de software, no 703 pruebas sobre el router.

Falta construir la interfaz y el asistente de IA explicativa, completar la validación final y cerrar la documentación.”

### Demo breve de Axl

Directorio de trabajo:

```powershell
Set-Location 'C:\Users\Gamer\Desktop\grupo-1\Proyecto-Titulo-Cisco-IOS'
$env:PYTHONUTF8='1'
```

Preparar antes de la exposición, sin proyección:

1. Abrir VirtualBox con CSR1000v encendida. Dejar visible solo la ventana necesaria, sin consola con direcciones, claves, nombres reales ni historial.
2. En VS Code abrir `scripts/evaluacion_2/run_csr1000v_validation.py`. Usar Buscar para mostrar únicamente `request_connection`, la llamada a `collect_and_analyze_device` dentro de `main`, y `render_result`.
3. Explicar que todas las entradas usan lectura oculta, las credenciales son transitorias y la salida imprime conteos, ID, estado y severidad. No mostrar el archivo entero ni configuraciones.
4. Si el responsable decide preparar una nueva ejecución manual autorizada, ejecutar antes de iniciar la exposición:

```powershell
.\.venv\Scripts\python.exe scripts\evaluacion_2\run_csr1000v_validation.py
```

El wrapper solicita host, puerto, usuario y contraseña con entrada oculta. Introducirlos personalmente antes de proyectar. No guardarlos en comandos, archivos, variables expuestas ni capturas. Mostrar solo el bloque final sanitizado. Un intento, sin reintento automático.

Durante la exposición:

1. Mostrar VirtualBox y los tres fragmentos de código preparados, durante unos 30 segundos.
2. Mostrar el resultado sanitizado, durante unos 20 segundos: 1 sesión, 1 desconexión, 8/8 comandos, 8 evidencias, 21 evaluaciones y 3 findings. Identificar honestamente si corresponde a la ejecución previa. No presentarlo como una nueva sesión en vivo.
3. Si hay tiempo, ejecutar en vivo la campaña OFFLINE:

```powershell
.\.venv\Scripts\python.exe scripts\evaluacion_2\run_validation_scenarios.py --summary-only
```

Alternativa de software, también OFFLINE:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

No ocultar el warning ni cambiar los números si una nueva ejecución arroja resultados distintos. Si el acceso real falla, mostrar el error sanitizado y conservar las capturas anteriores identificadas como evidencia previa. No inventar un éxito.

`show version` y `show ip ssh` son opcionales en una demostración manual: no proyectar toda la salida, pues puede incluir seriales, hostname y claves. Preferir los recortes ya revisados. NetAudit no ejecuta configuración.

## Lectura correcta de las métricas

| Evidencia | Qué demuestra | Resultado documentado |
|---|---|---|
| Suite pytest | Pruebas automatizadas de software | 703 passed, 1 warning externo Starlette/AnyIO |
| Campaña sintética | Comparación entre expectativas declaradas y motor en datos controlados | 3 escenarios, 21 reglas cada uno, 63/63, 0 diferencias, 0 errores de contrato |
| Estados sintéticos | Resultados calculados, no hallazgos de una red real | 32 PASS, 17 FAIL, 14 NOT_EVALUATED |
| CSR1000v | Validación manual real independiente | 1 sesión, 1 desconexión, 8/8 comandos, 8 evidencias, 21 evaluaciones, 3 findings |

NOT_EVALUATED significa información insuficiente dentro del contrato. No equivale necesariamente a un error. Los estados posibles son PASS, FAIL, NOT_APPLICABLE, NOT_EVALUATED y ERROR.

Findings reales: `IOS-NTP-001` MEDIUM, `IOS-LOG-001` MEDIUM e `IOS-AUTH-003` HIGH. Los recortes muestran filas independientes de la tabla, no toda la tabla real.

## Recortes utilizados de Capturas.docx

Se revisaron visualmente las cuatro páginas. Se extrajeron las imágenes originales incrustadas y se recortaron sin reescribir resultados, reconstruir terminales ni generar capturas artificiales. El PPTX contiene únicamente los recortes sanitizados, no las capturas completas ocultas.

| Página | Recorte | Slide | Información excluida |
|---|---|---:|---|
| 1, imagen superior | Tres líneas de versión y plataforma IOS XE | 3 | Prompt, uptime y resto de la consola |
| 1, imagen inferior | Línea KEX con los dos algoritmos ofrecidos | 2 | Clave pública, prompt y otras líneas SSH |
| 2 | VALIDACIÓN REAL, plataforma, solo lectura, sesión, desconexión y 8/8 | 3 | Comandos previos, rutas locales y entradas de conexión |
| 2 | Conteos de evidencias, evaluaciones y findings | 3 | Resto de la terminal |
| 2 | Cabecera, filas NTP/Syslog y fila AUTH-003 en recortes separados | 3 | Otras filas y consola de entrada |
| 4 | Línea original 703 passed, 1 warning, 7.89s | 3 | Rutas de usuario y resto del warning |
| 4 | Cabecera FUENTES SINTÉTICAS, escenarios, reglas, comparaciones, coincidencias y diferencias | 3 | Comandos anteriores y rutas locales |
| 4 | Línea de errores de contrato igual a cero | 3 | Resto de la terminal |

La página 3 no se incorporó: contiene direcciones e identidad del laboratorio y un prompt de configuración. No es una evidencia apropiada para representar el flujo read-only de NetAudit. La línea KEX de la página 1 basta para respaldar el diagnóstico del laboratorio.

### Capturas que conviene reemplazar

- Sustituir la página 3 completa antes de compartir públicamente el Word o entregar un informe: generar una captura manual de consulta de solo lectura y recortar únicamente el dato técnico necesario, sin IP, usuario, hostname, claves ni modo de configuración. No retocar los resultados existentes para simular otra salida.
- La imagen inferior de la página 1 tampoco debe compartirse completa porque muestra una clave pública y prompts. En la presentación se conserva solo la línea KEX.
- Los recortes de resultados de páginas 2 y 4 son utilizables. Una nueva captura de mayor resolución y fuente más grande sería una mejora opcional para proyectores de baja resolución, no una condición para cambiar los resultados actuales.

## Fuentes documentales

- Definición de Proyecto APT Fase 1, páginas 5–6: tareas, responsables y Carta Gantt.
- `Proyecto-Titulo-Cisco-IOS/README.md` y `docs/arquitectura.md`: flujo actual y alcance.
- `docs/catalogo-reglas.md`: 14 controles de configuración y 7 operacionales/multifuente.
- `docs/registro-controles-adicionales-evaluacion-2.md`: corte actual, campaña y compatibilidad SSH.
- `docs/registro-expansion-operacional-evaluacion-2.md`: ampliación a ocho comandos y límites operacionales.
- `Capturas.docx`, páginas 1–4: evidencia visual real proporcionada por el equipo.

La Evaluación 2 amplía la evidencia de validación del prototipo; no implica el cierre del proyecto.

Las reglas detectan. La evidencia demuestra. La IA explica. El último componente sigue planificado, no implementado.
