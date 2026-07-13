from __future__ import annotations

from ios_auditor.domain import (
    AnalysisContext,
    Evidence,
    RuleEvaluation,
    RuleStatus,
    Severity,
)


def _find_line_number(context: AnalysisContext, target: str) -> int | None:
    for index, line in enumerate(context.original_content.splitlines(), start=1):
        if line.strip() == target:
            return index
    return None


def _evidence(
    context: AnalysisContext, content: str, line_number: int | None
) -> Evidence:
    return Evidence(
        source=context.source_path,
        sha256=context.sha256,
        line_number=line_number,
        content=content,
    )


class TelnetVtyRule:
    rule_id = "IOS-ADM-001"
    name = "Telnet permitido en líneas VTY"
    severity = Severity.HIGH
    recommendation = "Restringir el acceso remoto a SSH mediante 'transport input ssh'."

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        telnet_evidence: list[Evidence] = []
        all_sections_only_ssh = bool(context.vty_sections)

        for section in context.vty_sections:
            if not section.transport_inputs:
                all_sections_only_ssh = False
                continue
            for line_number, protocols in section.transport_inputs:
                if "telnet" in protocols:
                    telnet_evidence.append(
                        _evidence(
                            context,
                            f"transport input {' '.join(protocols)}",
                            line_number or None,
                        )
                    )
                if protocols != ("ssh",):
                    all_sections_only_ssh = False

        if telnet_evidence:
            status = RuleStatus.FAIL
            message = "Una o más secciones VTY permiten Telnet."
            evidence = tuple(telnet_evidence)
        elif all_sections_only_ssh:
            status = RuleStatus.PASS
            message = "Todas las secciones VTY permiten únicamente SSH."
            evidence = ()
        else:
            status = RuleStatus.NOT_EVALUATED
            message = "No hay secciones VTY suficientes para evaluar el transporte remoto."
            evidence = ()

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.name,
            status=status,
            severity=self.severity,
            message=message,
            recommendation=self.recommendation,
            evidence=evidence,
        )


class HttpServerRule:
    rule_id = "IOS-SRV-001"
    name = "Servidor HTTP sin cifrado habilitado"
    severity = Severity.MEDIUM
    recommendation = (
        "Deshabilitar HTTP si no es necesario y evaluar HTTPS cuando corresponda."
    )

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        target = "ip http server"
        exists = target in context.normalized_lines
        evidence = (
            (_evidence(context, target, _find_line_number(context, target)),)
            if exists
            else ()
        )
        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.name,
            status=RuleStatus.FAIL if exists else RuleStatus.PASS,
            severity=self.severity,
            message=(
                "El servidor HTTP sin cifrado está habilitado."
                if exists
                else "El servidor HTTP sin cifrado no está habilitado."
            ),
            recommendation=self.recommendation,
            evidence=evidence,
        )


class EnablePasswordRule:
    rule_id = "IOS-AUTH-001"
    name = "Enable password sin enable secret"
    severity = Severity.HIGH
    recommendation = "Utilizar enable secret y retirar enable password."

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        password_lines = tuple(
            line for line in context.normalized_lines if line.startswith("enable password ")
        )
        secret_exists = any(
            line.startswith("enable secret ") for line in context.normalized_lines
        )

        if secret_exists:
            status = RuleStatus.PASS
            message = "Existe enable secret para proteger el acceso privilegiado."
            evidence: tuple[Evidence, ...] = ()
        elif password_lines:
            status = RuleStatus.FAIL
            message = "Existe enable password sin enable secret."
            evidence = tuple(
                _evidence(
                    context,
                    "enable password <REDACTED>",
                    _find_line_number(context, line),
                )
                for line in password_lines
            )
        else:
            status = RuleStatus.NOT_APPLICABLE
            message = "No existe enable password ni enable secret."
            evidence = ()

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.name,
            status=status,
            severity=self.severity,
            message=message,
            recommendation=self.recommendation,
            evidence=evidence,
        )


PILOT_RULES = (TelnetVtyRule(), HttpServerRule(), EnablePasswordRule())
