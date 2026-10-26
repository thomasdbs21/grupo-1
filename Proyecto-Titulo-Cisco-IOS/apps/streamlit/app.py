"""Ejecutar desde la raíz técnica: python -m streamlit run apps/streamlit/app.py."""
import streamlit as st

from ios_auditor.ui.backend import BackendClient, BackendError

AI_UNAVAILABLE = (
    "La explicación mediante IA no está disponible. Los resultados deterministas "
    "del análisis siguen siendo válidos."
)


def show_explanation(result: dict) -> None:
    explanation = result["explanation"]
    st.write(explanation["summary"])
    for item in explanation["findings"]:
        with st.expander(item["rule_id"]):
            st.write(item["explanation"])
            st.write("**Impacto técnico:**", item["technical_impact"])
            st.write("**Motivo de prioridad:**", item["priority_reason"])
            st.write("**Revisión manual:**", item["manual_review"])
    if explanation.get("question_answer"):
        st.write(explanation["question_answer"])
    for limitation in explanation["limitations"]:
        st.caption(limitation)
    if result.get("context_truncated"):
        st.warning("La explicación utiliza un contexto acotado; no incluye todos los fragmentos del análisis.")


def main() -> None:
    st.set_page_config(page_title="NetAudit", layout="wide")
    st.title("NetAudit")
    st.caption("Las reglas detectan. La evidencia demuestra. La IA explica.")
    if st.session_state.pop("_clear_device_credentials", False):
        for key in ["device_host", "device_username", "device_password"]:
            st.session_state[key] = ""
    client = BackendClient()
    mode = st.radio("Modo de análisis", ["Analizar archivo", "Analizar dispositivo"], horizontal=True)
    result = None
    if mode == "Analizar archivo":
        with st.form("file-analysis", clear_on_submit=True):
            uploaded = st.file_uploader("Configuración Cisco IOS/IOS XE", type=["cfg", "conf", "txt"])
            submit = st.form_submit_button("Analizar")
        if submit:
            if uploaded is None:
                st.warning("Selecciona un archivo de configuración.")
            else:
                try:
                    with st.spinner("Analizando mediante reglas deterministas…"):
                        result = client.analyze_file(uploaded.name, uploaded.getvalue())
                except BackendError:
                    st.error("No fue posible analizar el archivo. Revisa que FastAPI esté iniciado y que el archivo sea válido.")
    else:
        st.info("Solo consultas autorizadas de lectura. El dispositivo debe pertenecer a tu laboratorio autorizado.")
        with st.form("device-analysis", clear_on_submit=True):
            host = st.text_input("Host IPv4 privado", key="device_host")
            port = st.number_input("Puerto SSH", min_value=1, max_value=65535, value=22)
            username = st.text_input("Usuario", key="device_username")
            password = st.text_input("Contraseña", type="password", key="device_password")
            submit = st.form_submit_button("Analizar dispositivo")
        if submit:
            try:
                with st.spinner("Recopilando evidencia de solo lectura…"):
                    result = client.analyze_device(host, int(port), username, password)
            except BackendError:
                st.session_state["_device_error"] = True
            finally:
                st.session_state["_clear_device_credentials"] = True
                password = ""
                username = ""
                host = ""
    if result is not None:
        st.session_state["analysis"] = result
        st.session_state["explanation"] = None
        st.session_state["chat"] = []
    if st.session_state.get("_clear_device_credentials"):
        st.rerun()
    if st.session_state.pop("_device_error", False):
        st.error("No fue posible analizar el dispositivo. Revisa los datos y la disponibilidad del laboratorio.")
    analysis = st.session_state.get("analysis")
    if analysis is None:
        return
    reference = analysis.get("analysis_id") or analysis.get("execution_id")
    st.subheader("Resultados deterministas")
    st.caption("Referencia del análisis: " + reference)
    columns = st.columns(6)
    columns[0].metric("Evaluaciones", analysis["total_evaluations"])
    for col, status in zip(columns[1:], ["PASS", "FAIL", "NOT_APPLICABLE", "NOT_EVALUATED", "ERROR"]):
        col.metric(status, analysis["status_summary"].get(status, 0))
    st.subheader("Findings")
    if not analysis["findings"]:
        st.success("El motor no produjo Findings en este análisis.")
    for finding in analysis["findings"]:
        with st.expander(f'{finding["rule_id"]} · {finding["rule_name"]} · {finding["severity"]}'):
            st.write(finding["message"])
            st.write("**Recomendación:**", finding["recommendation"])
            for evidence in finding["evidence"]:
                st.code(evidence["content"], language="text")
    st.subheader("Explicación con IA")
    if st.button("Explicar hallazgos"):
        try:
            with st.spinner("Solicitando una explicación de los Findings existentes…"):
                st.session_state["explanation"] = client.explain(reference)
        except BackendError:
            st.warning(AI_UNAVAILABLE)
    if st.session_state.get("explanation"):
        show_explanation(st.session_state["explanation"])
    st.subheader("Pregunta sobre este análisis")
    for message in st.session_state.get("chat", []):
        with st.chat_message(message["role"]):
            st.write(message["content"])
    question = st.chat_input("Pregunta sobre este análisis", max_chars=500)
    if question:
        try:
            with st.spinner("Consultando los Findings de este análisis…"):
                answer = client.explain(reference, question)["explanation"]
            text = answer.get("question_answer") or answer["summary"]
            st.session_state.setdefault("chat", []).extend([
                {"role": "user", "content": question}, {"role": "assistant", "content": text},
            ])
            st.rerun()
        except BackendError:
            st.warning(AI_UNAVAILABLE)


main()
