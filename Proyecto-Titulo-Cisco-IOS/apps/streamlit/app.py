"""Interfaz de Fase 2. Ejecutar: python -m streamlit run apps/streamlit/app.py."""
from datetime import datetime
from html import escape
import time

import streamlit as st

from ios_auditor.ui.backend import BackendClient, BackendError
from ios_auditor.ui.presentation import (
    SEVERITIES, STATUSES, csv_export, error_message, filtered_findings,
    json_export, safe_result, safe_text, service_badges, severity_counts,
)

AI_UNAVAILABLE = (
    'La explicación mediante IA no está disponible. Los resultados deterministas '
    'del análisis siguen siendo válidos.'
)
STATUS_COLORS = {'PASS': 'green', 'FAIL': 'red', 'NOT_APPLICABLE': 'gray',
                 'NOT_EVALUATED': 'orange', 'ERROR': 'red'}
SEVERITY_COLORS = {'CRITICAL': 'red', 'HIGH': 'red', 'MEDIUM': 'orange', 'LOW': 'blue', 'INFO': 'gray'}

def reset_analysis():
    for key in list(st.session_state):
        if key in ('analysis', 'explanation', 'chat', '_analysis_received_at', '_analysis_origin',
                   '_ai_error', '_ai_last_success', '_form_error', 'analysis_tabs') or key.startswith('filter_'):
            del st.session_state[key]

def health_snapshot(client):
    refresh = st.session_state.pop('_refresh_health', False)
    if refresh or time.monotonic() - st.session_state.get('_health_checked', 0) > 60:
        st.session_state['_health'] = client.system_status()
        st.session_state['_health_checked'] = time.monotonic()
        if refresh and (st.session_state['_health'].get('ai') or {}).get('gateway_reachable'):
            if st.session_state.get('_ai_error') == 'AI_GATEWAY_UNAVAILABLE':
                st.session_state.pop('_ai_error', None)
                st.session_state['_ai_last_success'] = False
    return st.session_state.get('_health', {})

def badge(label, value, tone):
    st.markdown(f'<div class="na-service"><span class="na-dot na-{tone}" aria-hidden="true"></span>'
                f'<span><strong>{escape(label)}</strong><br><span class="na-service-detail">{escape(value)}</span></span></div>',
                unsafe_allow_html=True)

def evidence_view(items, reference):
    for evidence in items:
        metadata = [f"Fuente: {safe_text(evidence['source'])}" if evidence.get('source') else '',
                    f"Línea: {evidence['line_number']}" if evidence.get('line_number') is not None else '']
        st.caption(' · '.join(x for x in metadata if x))
        if evidence.get('sha256'):
            st.text('SHA-256: ' + evidence['sha256'])
        if evidence.get('content'):
            st.code(evidence['content'], language='text', wrap_lines=True)
    st.caption('Referencia: ' + reference)

def show_explanation(result):
    explanation = result['explanation']
    st.write(explanation['summary'])
    for item in explanation['findings']:
        with st.expander(item['rule_id']):
            st.write(item['explanation'])
            st.write('**Impacto técnico:**', item['technical_impact'])
            st.write('**Motivo de prioridad:**', item['priority_reason'])
            st.write('**Revisión manual:**', item['manual_review'])
    if explanation.get('question_answer'):
        st.write(explanation['question_answer'])
    for limitation in explanation['limitations']:
        st.caption(limitation)
    if result.get('context_truncated'):
        st.warning('La explicación utiliza un contexto acotado; no incluye todos los fragmentos del análisis.')

def ask_ai(client, reference, question=None):
    try:
        with st.spinner('Solicitando explicación de los Findings existentes…'):
            response = client.explain(reference, question)
        st.session_state['_ai_last_success'] = response.get('source') == 'ai'
        st.session_state.pop('_ai_error', None)
        return response
    except BackendError as exc:
        st.session_state['_ai_error'] = exc.code
        st.session_state['_ai_last_success'] = False
        st.session_state['_health_checked'] = 0
        return None

def sidebar(client):
    result = None
    with st.sidebar:
        st.markdown('### NETAUDIT')
        st.caption('AUDITORÍA DE REDES')
        st.divider()
        st.markdown('**ANÁLISIS**')
        mode = st.radio('Origen de análisis', ['Analizar archivo', 'Analizar dispositivo'],
                        format_func=lambda x: 'Archivo' if x == 'Analizar archivo' else 'Dispositivo')
        if mode == 'Analizar archivo':
            with st.form('file-analysis', clear_on_submit=True):
                uploaded = st.file_uploader('Configuración Cisco IOS/IOS XE', type=['cfg', 'conf', 'txt'])
                st.caption('UTF-8 · hasta 2 MiB · sin modificar el archivo original')
                submit = st.form_submit_button('Analizar archivo', type='primary', width='stretch')
            if submit:
                if uploaded is None:
                    st.session_state['_form_error'] = 'Selecciona un archivo de configuración.'
                else:
                    try:
                        with st.spinner('Analizando mediante reglas deterministas…'):
                            result = client.analyze_file(uploaded.name, uploaded.getvalue())
                    except BackendError as exc:
                        st.session_state['_form_error'] = error_message(exc.code, 'file')
        else:
            st.markdown('**CONEXIÓN**')
            with st.form('device-analysis', clear_on_submit=True):
                host = st.text_input('Host IPv4 privado', key='device_host', placeholder='Dirección del laboratorio')
                port = st.number_input('Puerto SSH', min_value=1, max_value=65535, value=22)
                username = st.text_input('Usuario', key='device_username')
                password = st.text_input('Contraseña', type='password', key='device_password')
                st.caption('Solo consultas de lectura en tu laboratorio autorizado.')
                submit = st.form_submit_button('Analizar dispositivo', type='primary', width='stretch')
            if submit:
                try:
                    with st.spinner('Recopilando evidencia de solo lectura…'):
                        result = client.analyze_device(host, int(port), username, password)
                except BackendError as exc:
                    st.session_state['_form_error'] = error_message(exc.code, 'device')
                finally:
                    st.session_state['_clear_device_credentials'] = True
                    host = username = password = ''
        if result is not None:
            reset_analysis()
            st.session_state.update(analysis=result, explanation=None, chat=[],
                                    _analysis_origin=mode, _analysis_received_at=datetime.now().astimezone().isoformat())
        if st.session_state.get('_clear_device_credentials'):
            st.rerun()
        if st.session_state.get('_form_error'):
            st.error(st.session_state['_form_error'])
        st.divider()
        st.markdown('**ESTADO DEL SISTEMA**')
        if st.button('Actualizar estado', width='stretch', type='tertiary'):
            st.session_state['_refresh_health'] = True
        health = health_snapshot(client)
        for args in service_badges(health, st.session_state.get('_ai_last_success', False), st.session_state.get('_ai_error', '')):
            badge(*args)
        st.caption('Comprobaciones al abrir y cada 60 s al interactuar. Sin inferencias de prueba ni polling automático.')
        st.divider()
        st.markdown('**MODELO VALIDADO**')
        st.write('Gemini 3.5 Flash-Lite')
        st.caption('Google AI Studio · configuración del baseline. El health no expone el modelo activo.')
        st.caption('Tema claro/oscuro: menú ⋮ → Light / Dark.')

def main():
    st.set_page_config(page_title='NetAudit · Auditoría de redes', layout='wide', page_icon=':material/hub:')
    dark = st.context.theme.type == 'dark'
    accent = '#90bfff' if dark else '#225bba'
    st.markdown(f'''<style>
    .st-key-workspace{{max-width:1480px;margin-inline:auto;margin-top:-2rem;}}
    .st-key-identity{{gap:.4rem;}}
    .st-key-identity h1{{font-size:2.2rem;padding:.2rem 0;margin:0;}}
    .st-key-identity h4{{font-size:1.12rem;padding:.15rem 0;margin:0;}}
    .st-key-identity p{{margin-bottom:.2rem;}}
    .na-kicker{{color:{accent};font-size:.75rem;font-weight:700;letter-spacing:.12em;}}
    .na-service{{display:flex;gap:.65rem;align-items:flex-start;margin:.8rem 0;font-size:.85rem;line-height:1.4;}}
    .na-service-detail{{opacity:.78;font-size:.78rem;}}
    .na-dot{{width:.5rem;height:.5rem;border-radius:50%;flex:none;margin-top:.35rem;}}
    .na-ok{{background:{'#67dd9a' if dark else '#187641'};}}
    .na-warn{{background:{'#ffd079' if dark else '#996400'};}}
    .na-error{{background:{'#ff9b9b' if dark else '#b42332'};}}
    .na-muted{{background:{'#a3adbd' if dark else '#667085'};}}
    </style>''', unsafe_allow_html=True)
    if st.session_state.pop('_clear_device_credentials', False):
        for key in ('device_host', 'device_username', 'device_password'):
            st.session_state[key] = ''
    client = BackendClient()
    sidebar(client)
    with st.container(key='workspace'):
        with st.container(horizontal=True, vertical_alignment='center', horizontal_alignment='distribute'):
            st.markdown('<span class="na-kicker">AUDITORÍA DE INFRAESTRUCTURA</span>', unsafe_allow_html=True)
            if st.session_state.get('analysis') is not None:
                st.button('Nuevo análisis', on_click=reset_analysis, type='secondary')
        with st.container(key='identity'):
            st.title('NetAudit')
            st.markdown('#### Auditor inteligente de configuraciones Cisco IOS/IOS XE')
            st.write('Análisis determinista en modo de solo lectura con explicación asistida por IA.')
            st.caption('Las reglas detectan. La evidencia demuestra. La IA explica.')
        st.divider()
        raw = st.session_state.get('analysis')
        if raw is None:
            with st.container(border=True):
                st.subheader('Seleccione un origen de análisis para comenzar.')
                st.write('Configura el origen en el panel lateral. Los resultados y la evidencia aparecerán aquí al finalizar.')
                with st.container(horizontal=True):
                    with st.container(border=True, width='stretch'):
                        st.markdown('**01 · Analizar archivo**')
                        st.write('Carga una configuración Cisco IOS/IOS XE. El motor evalúa las reglas de configuración sin conectarse a un dispositivo.')
                    with st.container(border=True, width='stretch'):
                        st.markdown('**02 · Analizar dispositivo**')
                        st.write('Recopila las evidencias autorizadas mediante una sesión SSH de solo lectura y ejecuta el análisis integral.')
            st.info('La explicación y la conversación con IA son opcionales. El análisis determinista funciona de forma independiente.')
            return
        analysis = safe_result(raw)
        reference = raw.get('analysis_id') or raw.get('execution_id')
        with st.container(horizontal=True):
            st.badge('Análisis completado', color='blue')
            st.badge('Solo lectura', color='gray')
            st.caption('Archivo' if raw.get('analysis_id') else 'Análisis integral')
        st.caption('Referencia: ' + reference)
        health_ai = st.session_state.get('_health', {}).get('ai') or {}
        if st.session_state.get('_ai_error') or (health_ai.get('enabled') and not health_ai.get('gateway_reachable')):
            st.warning(AI_UNAVAILABLE)
        tabs = st.tabs(['Resumen', 'Hallazgos', 'Asistente IA', 'Evidencia'], key='analysis_tabs')
        with tabs[0]:
            st.subheader('Resultados deterministas')
            with st.container(horizontal=True, gap='small'):
                with st.container(border=True, width=180, key='kpi_total'):
                    st.badge('TOTAL', color='blue')
                    st.metric('Total de resultados', raw['total_evaluations'], label_visibility='collapsed')
                for status in STATUSES:
                    with st.container(border=True, width=170, key='kpi_' + status):
                        st.badge(status, color=STATUS_COLORS[status])
                        st.metric(status, raw['status_summary'].get(status, 0), label_visibility='collapsed')
            with st.container(border=True):
                st.markdown('**Información del análisis**')
                st.text('Origen: ' + analysis.get('source_name', 'Dispositivo · identidad no publicada por el backend'))
                st.text('Familia admitida: Cisco IOS / IOS XE')
                st.text('Fecha del backend: ' + raw.get('created_at', next((e.get('collected_at', '') for e in analysis.get('evidences', [])), 'No disponible')))
                if st.session_state.get('_analysis_received_at'):
                    st.caption('Recibido en esta sesión: ' + st.session_state['_analysis_received_at'])
                st.text(f"Findings: {raw['total_findings']} · Evidencias de comandos: {len(analysis.get('evidences', [])) if 'evidences' in analysis else 'No corresponde al modo archivo'}")
                st.caption('Hostname, IP y versión no se infieren: el DTO actual no los publica.')
            st.markdown('**Distribución de Findings por severidad**')
            counts = severity_counts(raw)
            with st.container(horizontal=True):
                for severity in SEVERITIES:
                    st.badge(f'{severity} · {counts.get(severity, 0)}', color=SEVERITY_COLORS[severity])
            st.caption('Los contadores proceden del resultado del backend. Una regla no analizada no equivale a PASS.')
            st.markdown('**Exportar este análisis**')
            with st.container(horizontal=True):
                st.download_button('Descargar resultado JSON', json_export(raw), 'netaudit_resultado.json', 'application/json', on_click='ignore')
                st.download_button('Descargar Findings CSV', csv_export(raw), 'netaudit_findings.csv', 'text/csv', on_click='ignore')
            st.caption('Incluyen todos los Findings, independientemente de los filtros. Evidencia redactada; sin credenciales de conexión ni salida cruda.')
        with tabs[1]:
            st.subheader('Hallazgos')
            with st.container(horizontal=True):
                severities = st.multiselect('Severidad', SEVERITIES, key='filter_severity', width=260)
                rules = st.multiselect('Regla', sorted({f['rule_id'] for f in raw['findings']}), key='filter_rule', width=260)
                query = st.text_input('Buscar hallazgo', key='filter_query', placeholder='rule_id, nombre, mensaje o recomendación', width=360)
            visible = filtered_findings(analysis, severities, rules, query)
            st.caption(f"{len(visible)} de {raw['total_findings']} Findings · orden por severidad y regla")
            if not raw['findings']:
                st.success('El motor no produjo Findings en este análisis.')
            elif not visible:
                st.info('No hay coincidencias con estos filtros. El resultado original permanece intacto.')
            for finding in visible:
                with st.container(border=True):
                    with st.container(horizontal=True):
                        st.markdown('**' + finding['rule_id'] + '**')
                        st.badge(finding['severity'], color=SEVERITY_COLORS.get(finding['severity'], 'gray'))
                    st.markdown('**' + finding['rule_name'] + '**')
                    st.write(finding['message'])
                    st.write('**Recomendación:**', finding['recommendation'])
                    with st.expander('Ver evidencia técnica · ' + finding['rule_id']):
                        evidence_view(finding['evidence'], reference)
        with tabs[2]:
            st.subheader('Explicación asistida por IA')
            st.info('La IA explica hallazgos previamente determinados por el motor. No modifica configuraciones, estados, severidades ni evidencia.')
            st.caption('Modelo validado: Gemini 3.5 Flash-Lite · Google AI Studio')
            badge(*service_badges(st.session_state.get('_health', {}), st.session_state.get('_ai_last_success', False), st.session_state.get('_ai_error', ''))[-1])
            if st.button('Explicar hallazgos', type='primary'):
                response = ask_ai(client, reference)
                if response is not None:
                    st.session_state['explanation'] = response
                st.rerun()
            if st.session_state.get('explanation'):
                show_explanation(st.session_state['explanation'])
            st.divider()
            st.markdown('**Pregunta sobre este análisis**')
            st.caption('La conversación dura solo esta sesión y se limita al análisis seleccionado.')
            for message in st.session_state.get('chat', []):
                with st.chat_message(message['role']):
                    st.write(message['content'])
            question = st.chat_input('Pregunta sobre este análisis', max_chars=500)
            if question:
                question = safe_text(question)[:500]
                response = ask_ai(client, reference, question)
                if response is not None:
                    answer = response['explanation']
                    text = answer.get('question_answer') or answer['summary']
                    st.session_state.setdefault('chat', []).extend([
                        {'role': 'user', 'content': question}, {'role': 'assistant', 'content': safe_text(text)}])
                st.rerun()
        with tabs[3]:
            st.subheader('Evidencia técnica')
            st.caption('Solo fragmentos sanitizados y metadatos publicados por el backend. Las salidas crudas no están disponibles en esta vista.')
            for index, evidence in enumerate(analysis.get('evidences', []), 1):
                with st.expander(f"{index:02} · {evidence.get('command', 'Evidencia')}"):
                    st.text('Execution ID: ' + reference)
                    st.text('Fecha: ' + evidence.get('collected_at', 'No disponible'))
                    st.text('SHA-256 original: ' + evidence.get('raw_output_sha256', 'No disponible'))
            for finding in analysis['findings']:
                with st.expander(f"{finding['rule_id']} · fragmentos del Finding"):
                    evidence_view(finding['evidence'], reference)

main()
