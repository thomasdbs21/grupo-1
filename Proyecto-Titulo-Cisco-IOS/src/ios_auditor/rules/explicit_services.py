"""Política de endurecimiento basada solo en directivas globales explícitas."""

from dataclasses import dataclass
from typing import ClassVar

from ios_auditor.domain import AnalysisContext, RuleEvaluation, RuleMetadata, RuleStatus
from ios_auditor.rules.evaluation2 import _blocks, _result


# Resuelve habilitación, negación o incertidumbre de una directiva global explícita.
@dataclass(frozen=True, slots=True)
class ExplicitDirectiveRule:
    metadata: RuleMetadata
    commands: ClassVar[tuple[tuple[str, ...], ...]]

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        """Conserva la línea de evidencia; la ausencia o contradicción impide decidir."""
        states = {}
        for block in _blocks(context):
            tokens = tuple(token.lower() for token in block.head.tokens)
            if tokens == ("end",):
                break
            # Un macro puede contener líneas sin sangría que aún no se han aplicado.
            if tokens[:2] == ("macro", "name") or (tokens[:1] == ("banner",) and block.head.tokens[0] != "banner"):
                return _result(self.metadata, context, RuleStatus.NOT_EVALUATED,
                               "Bloque multilínea fuera del subconjunto evaluable.")
            negated = tokens[:1] == ("no",)
            default = tokens[:1] == ("default",)
            body = tokens[1:] if negated or default else tokens
            if not any(body[:len(command)] == command for command in self.commands):
                continue
            if body not in self.commands or default or block.children:
                return _result(self.metadata, context, RuleStatus.NOT_EVALUATED,
                               "Directiva reconocida con forma no evaluable.", block.head.number)
            states.setdefault(RuleStatus.PASS if negated else RuleStatus.FAIL, block.head.number)
        if len(states) != 1:
            return _result(self.metadata, context, RuleStatus.NOT_EVALUATED,
                           "Directiva ausente o contradictoria; no se infiere el valor efectivo.")
        status, line = next(iter(states.items()))
        directive = " ".join(self.commands[0])
        message = (f"{directive}: desactivación explícita." if status is RuleStatus.PASS
                   else f"{directive}: habilitación explícita; revisar la política.")
        return _result(self.metadata, context, status, message, line)


# Reconoce los alias ip finger y service finger dentro de la misma política.
class FingerRule(ExplicitDirectiveRule):
    expected_id = "IOS-SRV-003"
    commands = (("ip", "finger"), ("service", "finger"))


# Revisa la habilitación explícita del servicio PAD de X.25.
class PadRule(ExplicitDirectiveRule):
    expected_id = "IOS-SRV-004"
    commands = (("service", "pad"),)


# Revisa la directiva global explícita de source routing IPv4.
class SourceRouteRule(ExplicitDirectiveRule):
    expected_id = "IOS-IP-002"
    commands = (("ip", "source-route"),)
