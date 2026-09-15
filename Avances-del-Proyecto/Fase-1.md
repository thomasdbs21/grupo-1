# Fase 1

**Estado:** documentada.

## Definición y problema abordado

Durante la primera fase se definió NetAudit como un asistente para analizar configuraciones Cisco IOS e IOS XE. El problema abordado es la dificultad de revisar manualmente grandes volúmenes de configuración y de mantener criterios técnicos consistentes para detectar riesgos, controles ausentes, inconsistencias y malas prácticas.

El público objetivo comprende administradores de red, personal de soporte y equipos de operaciones responsables de infraestructura Cisco. La solución se diseñó como apoyo al análisis y no como una herramienta de administración automática.

## Arquitectura y principios

La arquitectura separa entrada, recopilación SSH, parsing, normalización, motor de reglas, servicios, API y futuras capas de persistencia, interfaz, reportes e inteligencia artificial.

Los principios principales son:

- operación de solo lectura;
- reglas técnicas deterministas;
- contextos de análisis normalizados e inmutables;
- trazabilidad de evidencias, evaluaciones y hallazgos;
- creación de hallazgos únicamente desde evaluaciones `FAIL`;
- sanitización de credenciales y datos sensibles;
- inteligencia artificial opcional y subordinada a los resultados técnicos.

## Laboratorio

Las validaciones reales de los Incrementos 4 a 8 utilizaron una CSR1000v con IOS XE 16.9.5 en VirtualBox. La recopilación remota se restringió a cuatro comandos `show` autorizados y no modificó el dispositivo. GNS3 no se presenta como plataforma ya utilizada; permanece como una posible ampliación futura condicionada a imágenes autorizadas.

## Desarrollo realizado

El avance técnico de esta fase comprende:

1. Analizador offline de archivos `running-config` con CiscoConfParse.
2. Reglas piloto y registro determinista basado en lógica Python y metadatos YAML.
3. API FastAPI para análisis de archivos locales.
4. Recopilación SSH de solo lectura mediante Netmiko.
5. Parsing TextFSM de `show version`, `show ip interface brief` y `show ip ssh`.
6. Orquestación integral de cuatro fuentes en una única sesión SSH.
7. Endpoint seguro para el análisis integral de dispositivos.
8. Ampliación controlada del catálogo hasta ocho reglas deterministas.

Al cierre del Incremento 8 se registraron 314 pruebas aprobadas. La definición del Incremento 9 quedó aprobada y planificada, sin implementación.

## Entregables académicos

Los documentos individuales se organizaron por estudiante y los documentos grupales se separaron en:

- [Entregables individuales](../Entregables-APT/Fase-1/Individuales/)
- [Entregables grupales](../Entregables-APT/Fase-1/Grupales/)

## Documentación técnica de referencia

- [Arquitectura](../Proyecto-Titulo-Cisco-IOS/docs/arquitectura.md)
- [Catálogo de reglas](../Proyecto-Titulo-Cisco-IOS/docs/catalogo-reglas.md)
- [Decisiones técnicas](../Proyecto-Titulo-Cisco-IOS/docs/decisiones-tecnicas.md)
- [Plan incremental](../Proyecto-Titulo-Cisco-IOS/docs/plan-incremental.md)
- [Definición del Incremento 9](../Proyecto-Titulo-Cisco-IOS/docs/definicion-incremento-9-persistencia-relacional.md)
- [README técnico](../Proyecto-Titulo-Cisco-IOS/README.md)
