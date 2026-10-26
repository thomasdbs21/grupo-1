"""Controles multifuente acotados; ninguna evidencia copia valores de entrada."""

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from ios_auditor.domain.models import (
    Evidence, InterfaceStatus, MultiSourceContext, OperationalContext, ProtocolStatus,
    RuleEvaluation, RuleMetadata, RuleStatus, ShowIpInterfaceBriefData,
)
from ios_auditor.domain.operational_sources import (
    ShowAccessListsData, ShowInterfacesData, ShowIpOspfNeighborData,
    ShowNtpAssociationsData,
)
from ios_auditor.rules.evaluation2 import _blocks
from ios_auditor.rules.metadata import load_metadata_files
from ios_auditor.rules.interface_unused import unused_interface_status
from ios_auditor.rules.registry import build_registry

PASS, FAIL, NA, NE = (
    RuleStatus.PASS, RuleStatus.FAIL, RuleStatus.NOT_APPLICABLE,
    RuleStatus.NOT_EVALUATED,
)

# Política histórica del prototipo, no SLA ni umbral universal Cisco.
MIN_OBSERVATIONS = 10_000
MIN_ERRORS = 100
ERROR_PERCENT = 1


def _source(context: MultiSourceContext, command: str, model: type) -> OperationalContext | None:
    return next((item for item in context.operational
                 if item.command == command and isinstance(item.data, model)), None)


def _combined(states: list[RuleStatus]) -> RuleStatus:
    if FAIL in states:
        return FAIL
    if NE in states:
        return NE
    return PASS if states else NA


def _descriptions(context: MultiSourceContext) -> RuleStatus:
    source = _source(context, "show ip interface brief", ShowIpInterfaceBriefData)
    if source is None:
        return NE
    active = [item.name for item in source.data.interfaces
              if item.status == InterfaceStatus.UP and item.protocol == ProtocolStatus.UP]
    if len(active) != len(set(active)):
        return NE
    blocks = _blocks(context.configuration)
    states = []
    for name in active:
        matches = [block for block in blocks if block.head.tokens == ("interface", name)]
        if len(matches) != 1:
            states.append(NE)
            continue
        descriptions = [line.tokens for line in matches[0].children
                        if line.tokens[:1] == ("description",)]
        negated = any(line.tokens[:2] == ("no", "description")
                      for line in matches[0].children)
        if len(descriptions) > 1 or (descriptions and negated):
            states.append(NE)
        elif descriptions:
            states.append(PASS if len(descriptions[0]) > 1 else NE)
        else:
            states.append(FAIL)
    return _combined(states)


def _acl_number(value: str) -> str | None:
    if not value.isdigit():
        return None
    number = int(value)
    if 1 <= number <= 99 or 1300 <= number <= 1999:
        return "standard"
    if 100 <= number <= 199 or 2000 <= number <= 2699:
        return "extended"
    return None


def _acl_application(context: MultiSourceContext) -> RuleStatus:
    source = _source(context, "show access-lists", ShowAccessListsData)
    if source is None or not source.data.recognized:
        return NE
    defined: dict[str, str] = {}
    applied: set[str] = set()
    ambiguous = False
    blocks = _blocks(context.configuration)
    for block in blocks:
        tokens = block.head.tokens
        if tokens[:2] == ("ip", "access-list"):
            if len(tokens) != 4 or tokens[2] not in {"standard", "extended"}:
                ambiguous = True
            elif tokens[3] in defined:
                ambiguous = True
            else:
                defined[tokens[3]] = tokens[2]
        elif tokens[:1] == ("access-list",):
            kind = _acl_number(tokens[1]) if len(tokens) >= 3 else None
            if kind is None:
                ambiguous = True
            else:
                defined[tokens[1]] = kind
        for line in (block.head,) + block.children:
            directive = line.tokens
            if directive[:1] == ("no",):
                continue
            if directive[:2] == ("ip", "access-group"):
                if (len(block.head.tokens) == 2 and block.head.tokens[0] == "interface"
                        and len(directive) == 4 and directive[3] in {"in", "out"}):
                    applied.add(directive[2])
                else:
                    ambiguous = True
            # Other ACL consumers require separate contracts. Their presence
            # blocks FAIL, even if the supported interface references are absent.
            elif (any(token in directive for token in (
                    "access-class", "access-group", "distribute-list", "traffic-filter"))
                  or directive[:1] == ("route-map",)
                  or directive[:2] in {("ip", "nat"), ("crypto", "map")}
                  or directive[:2] == ("snmp-server", "community")
                  and len(directive) > 4
                  or directive[:3] == ("ip", "http", "access-class")):
                ambiguous = True
    # Unknown consumers can reference an ACL by its exact identifier. Detect
    # references after collecting all definitions, regardless of CLI ordering.
    # This is deliberately conservative, not a general parser of ACL consumers.
    for block in blocks:
        if block.head.tokens[:2] == ("ip", "access-list") or block.head.tokens[:1] == ("access-list",):
            continue
        for line in (block.head,) + block.children:
            tokens = line.tokens
            if (tokens[:1] in {("no",), ("description",), ("remark",), ("hostname",)}
                    or tokens[:2] == ("ip", "access-group")):
                continue
            if any(name in tokens for name in defined):
                ambiguous = True
    operational = {item.name: item.kind for item in source.data.access_lists}
    if len(operational) != len(source.data.access_lists) or ambiguous:
        return NE
    if defined != operational or applied - defined.keys():
        return NE
    if not defined:
        return NA
    return PASS if defined.keys() <= applied else FAIL


def _ntp(context: MultiSourceContext) -> RuleStatus:
    source = _source(context, "show ntp associations", ShowNtpAssociationsData)
    if source is None or not source.data.recognized:
        return NE
    associations = source.data.associations
    if not associations:
        return NA
    if any(item.synchronized and item.stratum < 16 and item.reach > 0 for item in associations):
        return PASS
    return FAIL


def _counter_direction(packets: int | None, errors: int | None) -> RuleStatus:
    if packets is None or errors is None or packets < 0 or errors < 0:
        return NE
    total = packets + errors
    if total < MIN_OBSERVATIONS:
        return NE
    if errors >= MIN_ERRORS and errors * 100 > ERROR_PERCENT * total:
        return FAIL
    return PASS


def _availability(context: MultiSourceContext) -> RuleStatus:
    source = _source(context, "show interfaces", ShowInterfacesData)
    if source is None or not source.data.recognized:
        return NE
    active = [item for item in source.data.interfaces
              if item.status == "up" and item.protocol == "up"]
    states = [_counter_direction(packets, errors)
              for item in active for packets, errors in (
                  (item.input_packets, item.input_errors),
                  (item.output_packets, item.output_errors))]
    return _combined(states)


def _neighbors(context: MultiSourceContext) -> RuleStatus:
    source = _source(context, "show ip ospf neighbor", ShowIpOspfNeighborData)
    if source is None or not source.data.recognized:
        return NE
    processes = [block for block in _blocks(context.configuration)
                 if block.head.tokens[:2] == ("router", "ospf")]
    if not processes:
        return NA if not source.data.neighbors else NE
    if any(len(block.head.tokens) != 3 or not block.head.tokens[2].isdigit()
           or not 1 <= int(block.head.tokens[2]) <= 65535 for block in processes):
        return NE
    if not source.data.neighbors:
        return NE
    if all(item.state == "FULL" or (item.state, item.role) == ("2WAY", "DROTHER")
           for item in source.data.neighbors):
        return PASS
    # A snapshot cannot establish a missing expected neighbor or persistence.
    return NE


@dataclass(frozen=True, slots=True)
class ExpandedOperationalRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = ""

    def evaluate(self, context: MultiSourceContext) -> RuleEvaluation:
        if not isinstance(context, MultiSourceContext):
            raise TypeError("La regla requiere un contexto multifuente.")
        status = _CHECKS[self.metadata.id](context)
        message = _MESSAGES[self.metadata.id][status]
        sources = tuple(Evidence(item.command, item.sha256, None, message)
                        for item in context.operational
                        if item.command in self.metadata.required_sources)
        if "running-config" in self.metadata.required_sources:
            sources = (Evidence(context.configuration.source_path,
                                context.configuration.sha256, None, message),) + sources
        return RuleEvaluation(self.metadata.id, self.metadata.name, status,
                              self.metadata.default_severity, message,
                              self.metadata.recommendation, sources)


@dataclass(frozen=True, slots=True)
class InterfaceDescriptionRule(ExpandedOperationalRule):
    expected_id = "IOS-INT-002"


@dataclass(frozen=True, slots=True)
class AccessListApplicationRule(ExpandedOperationalRule):
    expected_id = "IOS-ACL-002"


@dataclass(frozen=True, slots=True)
class NtpSynchronizationRule(ExpandedOperationalRule):
    expected_id = "IOS-NTP-002"


@dataclass(frozen=True, slots=True)
class InterfaceErrorCountersRule(ExpandedOperationalRule):
    expected_id = "IOS-AVL-001"


@dataclass(frozen=True, slots=True)
class OspfNeighborExpectationRule(ExpandedOperationalRule):
    expected_id = "IOS-OSPF-002"


@dataclass(frozen=True, slots=True)
class UnusedInterfaceRule(ExpandedOperationalRule):
    expected_id = "IOS-INT-001"


OPERATIONAL_RULE_TYPES = (
    InterfaceDescriptionRule, AccessListApplicationRule, NtpSynchronizationRule,
    InterfaceErrorCountersRule, OspfNeighborExpectationRule, UnusedInterfaceRule,
)
_CHECKS = dict(zip((rule.expected_id for rule in OPERATIONAL_RULE_TYPES),
                   (_descriptions, _acl_application, _ntp, _availability, _neighbors,
                    unused_interface_status), strict=True))
_MESSAGES = {
    "IOS-INT-001": {PASS: "Interfaces correlacionadas operativas o administrativamente deshabilitadas.",
                    FAIL: "Interfaz física declarada sin uso, corroborada sin tráfico y explícitamente habilitada.",
                    NA: "Solo interfaces excluidas del control de puertos físicos.",
                    NE: "Sin uso no demostrado, estado discrepante o correlación insuficiente."},
    "IOS-INT-002": {PASS: "Interfaces activas correlacionadas con descripción.",
                    FAIL: "Interfaz activa evaluable sin descripción.",
                    NA: "Sin interfaces UP/UP dentro del alcance.",
                    NE: "No se puede correlacionar la descripción de forma segura."},
    "IOS-ACL-002": {PASS: "ACL IPv4 evaluables con aplicación configurada reconocida.",
                    FAIL: "ACL IPv4 evaluable sin aplicación configurada reconocida.",
                    NA: "Sin ACL IPv4 evaluables.",
                    NE: "Fuentes ACL discrepantes o mecanismo de aplicación no soportado."},
    "IOS-NTP-002": {PASS: "Existe una asociación NTP sincronizada según sys.peer.",
                    FAIL: "Asociaciones NTP evaluables sin sincronización.",
                    NA: "Tabla NTP reconocida sin asociaciones.",
                    NE: "Formato NTP desconocido o incompleto."},
    "IOS-AVL-001": {PASS: "Contadores acumulados evaluables bajo el umbral de alerta.",
                    FAIL: "Contadores acumulados superan el umbral histórico de alerta.",
                    NA: "Sin interfaces UP/UP evaluables.",
                    NE: "Contadores o muestra insuficientes; no se infiere salud actual."},
    "IOS-OSPF-002": {PASS: "Vecinos observados en estados aceptados; no certifica vecinos esperados.",
                     NA: "Sin OSPFv2 activo ni vecinos observados.",
                     NE: "Expectativa OSPF o estabilidad no demostrable con esta fotografía."},
}


@lru_cache(maxsize=1)
def get_expanded_operational_rules() -> tuple[ExpandedOperationalRule, ...]:
    directory = Path(str(files("ios_auditor.resources.rules")))
    metadata = load_metadata_files(directory, tuple(rule.expected_id + ".yaml"
                                                   for rule in OPERATIONAL_RULE_TYPES))
    # Reuse the deterministic metadata registry, without passing a config-only
    # context to multisource rules or mixing the two evaluation contracts.
    return build_registry(metadata, OPERATIONAL_RULE_TYPES).list_rules(enabled_only=True)
