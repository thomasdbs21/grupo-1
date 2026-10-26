"""Proyecciones de presentación: no evalúan reglas ni modifican el DTO del backend."""
from __future__ import annotations

import csv
from collections import Counter
from copy import deepcopy
from io import StringIO
import json
from typing import Any

# Reutilización de la función pura existente; no importa cliente ni servicio de IA.
from ios_auditor.ai.sanitization import sanitize_text

SEVERITIES = ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')
STATUSES = ('PASS', 'FAIL', 'NOT_APPLICABLE', 'NOT_EVALUATED', 'ERROR')
FINDING_FIELDS = ('rule_id', 'rule_name', 'severity', 'message', 'recommendation')
EVIDENCE_FIELDS = ('source', 'sha256', 'line_number', 'content')

def safe_text(value: Any) -> str:
    return sanitize_text(str(value))

def _evidence(item: dict) -> dict:
    return {k: (item[k] if k == 'line_number' else safe_text(item[k]))
            for k in EVIDENCE_FIELDS if k in item}

def _finding(item: dict, evaluation: bool = False) -> dict:
    fields = FINDING_FIELDS + (('status',) if evaluation else ())
    out = {k: (item[k] if k in ('rule_id', 'severity', 'status') else safe_text(item[k]))
           for k in fields if k in item}
    out['evidence'] = [_evidence(e) for e in item.get('evidence', [])]
    return out

def safe_result(analysis: dict) -> dict:
    """Lista explícita de campos exportables; excluye secretos y evidencia cruda."""
    out = {k: deepcopy(analysis[k]) for k in (
        'analysis_id', 'execution_id', 'sha256', 'created_at', 'status',
        'total_evaluations', 'total_findings', 'status_summary',
        'finding_severity_summary', 'operational_context_count') if k in analysis}
    if 'source_name' in analysis:
        out['source_name'] = safe_text(analysis['source_name'])
    out['findings'] = [_finding(f) for f in analysis.get('findings', [])]
    for key in ('evaluations', 'rule_evaluations'):
        if key in analysis:
            out[key] = [_finding(e, True) for e in analysis[key]]
    if 'evidences' in analysis:
        out['evidences'] = [{k: safe_text(e[k]) for k in
            ('command', 'collected_at', 'raw_output_sha256') if k in e}
            for e in analysis['evidences']]
    return out

def filtered_findings(analysis: dict, severities=(), rules=(), query: str = '') -> list[dict]:
    """Filtra y ordena una vista, sin cambiar Findings ni severidades."""
    query = query.strip().casefold()
    findings = [f for f in analysis.get('findings', [])
                if (not severities or f['severity'] in severities)
                and (not rules or f['rule_id'] in rules)
                and (not query or query in ' '.join(str(f.get(k, '')) for k in FINDING_FIELDS).casefold())]
    return sorted(findings, key=lambda f: (
        SEVERITIES.index(f['severity']) if f['severity'] in SEVERITIES else len(SEVERITIES), f['rule_id']))

def severity_counts(analysis: dict) -> dict:
    return dict(Counter(f['severity'] for f in analysis.get('findings', [])))

def json_export(analysis: dict) -> bytes:
    return json.dumps(safe_result(analysis), ensure_ascii=False, indent=2).encode('utf8')

def csv_export(analysis: dict) -> bytes:
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(FINDING_FIELDS + ('evidence',))
    for finding in safe_result(analysis)['findings']:
        values = [str(finding.get(k, '')) for k in FINDING_FIELDS]
        values.append('\n'.join(e.get('content', '') for e in finding['evidence']))
        # Evitar fórmulas al abrir el CSV en una hoja de cálculo.
        writer.writerow(["'" + v if v.lstrip().startswith(('=', '+', '-', '@'))
                         or v.startswith(('\t', '\r', '\n')) else v for v in values])
    return stream.getvalue().encode('utf-8-sig')

def service_badges(health: dict, last_ai_success: bool = False, ai_error: str = '') -> list[tuple[str, str, str]]:
    backend = health.get('backend', False)
    engine = health.get('engine', False)
    badges = [('NetAudit', 'En línea' if backend else 'No disponible', 'ok' if backend else 'error'),
              ('Motor determinista', 'Catálogo disponible' if engine else 'No comprobado', 'ok' if engine else 'warn')]
    ai = health.get('ai')
    if not backend or ai is None:
        return badges + [('OmniRoute', 'Estado no comprobado', 'muted'), ('IA', 'Estado no comprobado', 'muted')]
    if not ai.get('enabled'):
        return badges + [('OmniRoute', 'Consulta deshabilitada', 'muted'), ('IA', 'Deshabilitada', 'muted')]
    gateway = ai.get('gateway_reachable', False) and ai_error != 'AI_GATEWAY_UNAVAILABLE'
    badges.append(('OmniRoute', 'Accesible · HTTP' if gateway else 'No disponible', 'ok' if gateway else 'error'))
    if not ai.get('model_configured'):
        badges.append(('IA', 'Modelo no configurado', 'muted'))
    elif not gateway:
        badges.append(('IA', 'No disponible', 'error'))
    elif ai_error:
        badges.append(('IA', 'Última solicitud fallida', 'warn'))
    elif last_ai_success:
        badges.append(('IA', 'Disponible · respuesta verificada', 'ok'))
    else:
        badges.append(('IA', 'Configurada · sin inferencia de prueba', 'warn'))
    return badges

def error_message(code: str, origin: str = '') -> str:
    if code == 'DEVICE_TIMEOUT':
        return 'El dispositivo no respondió a tiempo. Revisa la conexión SSH y el laboratorio.'
    if code == 'DEVICE_ANALYSIS_FAILED':
        return 'No se pudo completar el análisis SSH. Revisa conectividad, acceso y credenciales; el backend no expone la causa interna.'
    if code in ('INVALID_EXTENSION', 'INVALID_ENCODING', 'EMPTY_FILE', 'UNANALYZABLE_CONFIG', 'FILE_TOO_LARGE'):
        return 'Archivo no válido. Usa una configuración UTF-8 .cfg, .conf o .txt de hasta 2 MiB.'
    if code == 'INVALID_REQUEST':
        return 'Revisa los campos del formulario. El destino debe ser una IPv4 privada y el puerto debe ser válido.'
    if origin == 'file':
        return 'No fue posible analizar el archivo. Revisa el archivo y la disponibilidad del backend.'
    return 'No fue posible completar la solicitud. Revisa la disponibilidad del backend e inténtalo nuevamente.'
