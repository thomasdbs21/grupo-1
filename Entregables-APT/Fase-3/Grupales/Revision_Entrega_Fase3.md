# Revisión de la entrega de Fase 3

Corte documental: 16 de noviembre de 2026. Se conservan el software, la presentación de defensa de once diapositivas y el video original. No se declara una entrega recibida en AVA.

## Video disponible

[Grabación original del grupo](https://drive.google.com/file/d/13xljM3MTVf63o-4bAlqgR-aTDXeMuSMA/view?usp=sharing): 156.187.296 bytes y **12:06,77**. El equipo decidió conservar el original sin recortar ni volver a grabar, aceptando el exceso de **2:06,77** sobre los diez minutos. Esta decisión no equivale a una autorización docente ni a cumplimiento del límite.

Google Drive es el único enlace oficial decidido por el equipo; no se solicita otra subida ni se modifica el video. La consulta actual mediante el conector confirma identidad, tipo MP4 y tamaño del archivo, pero no devuelve la lista de permisos; no se certifican lectura para evaluadores ni ausencia de edición. El antecedente anterior de edición por enlace no queda descartado. No se cambiaron permisos. El video permanece fuera de Git por tamaño. La elección de Drive difiere de la indicación de OneDrive Duoc de la guía; no se atribuye aprobación docente de esa diferencia.

## Tramos observados

Límites de los bloques de intervención obtenidos del VTT definitivo, con las pausas entre bloques sin asignar. La identificación se apoya en las presentaciones y transiciones orales, no en identificación biométrica.

| Integrante | Apartado | Inicio | Término | Duración del bloque |
|---|---|---|---|---|
| Emilio Cortes | Apertura y problema | 00:00,460 | 00:54,960 | 00:54,500 |
| Axl Urrutia | Producto, Gantt y arquitectura | 00:56,210 | 02:44,420 | 01:48,210 |
| Maikol Mamani | Modalidades, motor y Ansible | 02:47,840 | 07:20,830 | 04:32,990 |
| Thomas Henriquez | Demostración y validación | 07:22,130 | 11:10,102 | 03:47,972 |
| Emilio Cortes | Conclusión | 11:12,070 | 12:05,750 | 00:53,680 |

El reparto individual supera la diferencia máxima de un minuto indicada en la guía complementaria. **La portada sí aparece al inicio y la diapositiva de prueba funcional sí aparece antes de la aplicación.** Se corrige la observación anterior basada en muestreo de imágenes; las once diapositivas aparecen en la grabación.

## Evidencias observables

| Momento aproximado | Evidencia | Alcance y límite |
|---|---|---|
| 01:30 | Gantt de 18 semanas y ocho actividades | Expone el cierre técnico; no acredita recepción de todos los entregables académicos. |
| 02:00 | Arquitectura y separación entre motor e IA | Explicación del diseño. |
| 04:00–05:22 | Código y conversión de FAIL a Finding | Capturas de código, no ejecución de un editor en vivo. |
| 07:45 | Archivo: 17 evaluaciones, 2 PASS, 12 FAIL, 3 NOT_EVALUATED | Análisis real del software sobre archivo; no equivale a una conexión SSH. |
| 08:02–08:25 | ACL y acceso remoto, evidencia y recomendación | Dos ejemplos entre doce hallazgos; no demuestra explotación. |
| 09:30 | Dispositivo: 24 evaluaciones, 7 PASS, 3 FAIL, 5 NOT_APPLICABLE, 9 NOT_EVALUATED | Ocho evidencias visibles en el video; no se realiza una conexión nueva en esta revisión. |
| 10:00 | Respuesta IA marcada como verificada en la interfaz | Evidencia histórica, sin nueva inferencia ni garantía de disponibilidad. |
| 10:30 | Panel con 852, 72/72, 24 y cero fallos | Corte técnico documentado; no se ejecutó nuevamente pytest. |

## Transcripción

[VTT definitivo](3.2_Transcripcion_Grupo1.vtt): **187 subtítulos**, cuatro participantes, tiempos crecientes dentro del video y sintaxis WEBVTT validada mediante FFmpeg. Se conservan las once correcciones confirmadas y las palabras efectivamente pronunciadas, incluida la cifra oral «802»; el corte técnico documentado de pruebas sigue siendo 852.

La frase final confirmada «Y el asistente de IA va a explicar los hallazgos» ocupa **10:03,500–10:07,120**, sin comprimirla artificialmente en un segundo. No quedan marcadores de palabras imposibles de identificar. Los respaldos, audio y borradores permanecen privados; no se generó otra transcripción.

## Documentos individuales

| Integrante | Diario 3.1 | Autoevaluación 3.2 | Acción pendiente |
|---|---|---|---|
| Axl Urrutia | Respuestas revisadas del ZIP; antecedentes iniciales contrastados con su Fase 1; todas las subpreguntas cubiertas | Nueva valoración personal aportada por Axl: 1 CL, 2 CL, 3 LI, 4 CL, 5 CL; inglés sin marcar. Justificaciones positivas con tiempos y duración real | Ratificar las observaciones de metodología, valoración oral e indicador 4.1; la propuesta no es una calificación docente |
| Thomas Henriquez | Archivo publicado intacto; propuesta privada de forma disponible | Archivo publicado intacto; propuesta privada sin elegir niveles | Revisión y aprobación de su autor |
| Maikol Mamani | Archivo publicado intacto; respuestas personales por completar | Archivo publicado intacto; no se eligen niveles en su nombre | Completar y aprobar sus documentos |
| Emilio Cortes | Archivo publicado intacto; respuestas personales por completar | Archivo publicado intacto; no se eligen niveles en su nombre | Completar y aprobar sus documentos |

El indicador 3 mantiene la valoración de Axl. La guía complementaria, parte C, contempla LI si se incumple tiempo y se cumple parte de la estructura; el descriptor de la rúbrica base no coincide exactamente con la situación observada. Se explica la discrepancia sin cambiar marcas ni atribuir una decisión a la docente.

En el indicador 5, Axl propone CL para la selección 2.3, 4.1 y 5.1. Los tres tienen evidencia visible, pero revisar políticas mediante ACL y acceso remoto no demuestra por sí solo la protección completa de activos de 4.1. Se conserva el 100% como propuesta personal, pendiente de ratificar aplicabilidad y alcance; no se presenta como cumplimiento completo verificado ni como una medición de toda la carrera. La guía específica de Redes considera inglés opcional y no evaluado; se conserva la fila original sin marca y no se calcula una nota reponderada.

## Material grupal y entregas

El [PDF del video](3.2_Presentacion_Grupo1.pdf) tiene doce páginas: tabla de segmentos anterior y once diapositivas originales sin alteraciones. El [informe 3.3](3.3_NetAudit_Informe_Cierre_Fase3.docx) conserva su corte anterior; este registro actualiza el estado posterior de la transcripción y los documentos de Axl sin modificar su contenido técnico.

1. Conservar el enlace oficial de Drive indicado arriba. Comprobar que la docente puede visualizar el video y que el vínculo no concede edición. El conector actual no permite certificar esos permisos; no se genera un enlace alternativo.
2. Entrega individual: completar o subir el diario 3.1 en AVA según su pauta. La guía complementaria indica publicar la autoevaluación 3.2 en GitHub, completada por su autor; no exige cargarla también en AVA salvo instrucción adicional de la docente. No usar propuestas de otros integrantes como documentos aprobados.
3. AVA grupal: presentar el vínculo del video y los archivos solicitados por la docente; VTT y PDF están disponibles en este repositorio. Conservar el comprobante de envío.
4. Dejar constancia del exceso de duración; su consecuencia académica corresponde a la docente.

No se modifican Fases 1 y 2, Avances-Tecnicos, Referencias, la presentación final, el MP4 ni los documentos de los otros integrantes. La modificación local preexistente de código se preserva fuera del commit.
