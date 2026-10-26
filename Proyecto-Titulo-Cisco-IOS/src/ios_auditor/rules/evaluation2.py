"""Controles estáticos acotados; ningún fragmento de entrada se publica como evidencia."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network
import re
from typing import ClassVar

from ios_auditor.domain import AnalysisContext, Evidence, RuleEvaluation, RuleMetadata, RuleStatus


@dataclass(frozen=True, slots=True)
class _Line:
    number: int
    tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Block:
    head: _Line
    children: tuple[_Line, ...]


def _blocks(context: AnalysisContext) -> tuple[_Block, ...]:
    """Vista local de directivas raíz/hijos IOS, no un parser general de CLI.

    Conserva indentación y números de línea. Comentarios y cuerpos de banner
    no se interpretan como comandos. Los contratos aceptan solo sintaxis acotada.
    """
    result: list[_Block] = []
    head: _Line | None = None
    children: list[_Line] = []
    delimiter: str | None = None
    for number, raw in enumerate(context.original_content.splitlines(), 1):
        stripped = raw.strip()
        if delimiter is not None:
            if delimiter in stripped:
                delimiter = None
            continue
        if not stripped or stripped.startswith("!"):
            continue
        tokens = tuple(stripped.split())
        if not raw[0].isspace():
            if head is not None:
                result.append(_Block(head, tuple(children)))
            head, children = _Line(number, tokens), []
            if tokens[:1] == ("banner",) and len(tokens) >= 3:
                # IOS muestra el delimitador como carácter único o como ^C.
                tail = stripped.split(None, 2)[2]
                marker = tail[:2] if tail.startswith("^") else tail[:1]
                if marker and marker not in tail[len(marker):]:
                    delimiter = marker
        elif head is not None:
            children.append(_Line(number, tokens))
    if head is not None:
        result.append(_Block(head, tuple(children)))
    return tuple(result)


def _result(metadata: RuleMetadata, context: AnalysisContext, status: RuleStatus,
            text: str, line: int | None = None) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=metadata.id, rule_name=metadata.name, status=status,
        severity=metadata.default_severity, message=text,
        recommendation=metadata.recommendation,
        evidence=(Evidence(source=context.source_path, sha256=context.sha256,
                           line_number=line, content=text),),
    )


def _aggregate(states: list[RuleStatus]) -> RuleStatus:
    if RuleStatus.FAIL in states:
        return RuleStatus.FAIL
    if not states or RuleStatus.NOT_EVALUATED in states:
        return RuleStatus.NOT_EVALUATED
    return RuleStatus.PASS


def _secret_payload(tokens: tuple[str, ...], types: set[str]) -> bool:
    return (len(tokens) == 1 and tokens[0] not in types) or (
        len(tokens) == 2 and tokens[0] in types
    )


def _local_secret_exists(blocks: tuple[_Block, ...]) -> bool:
    for block in blocks:
        tokens = block.head.tokens
        if len(tokens) >= 4 and tokens[0] == "username":
            index = 2
            if tokens[index:index + 1] == ("privilege",):
                if len(tokens) < 6 or not tokens[index + 1].isdigit():
                    continue
                index += 2
            if tokens[index:index + 1] == ("secret",) and _secret_payload(
                tokens[index + 1:], {"0", "5", "8", "9"}
            ):
                return True
    return False


def _console_state(block: _Block, blocks: tuple[_Block, ...]) -> RuleStatus:
    children = tuple(line.tokens for line in block.children)
    aaa = any(item.head.tokens == ("aaa", "new-model") for item in blocks)
    logins = [tokens for tokens in children if tokens[:1] == ("login",)]
    if len(logins) > 1:
        return RuleStatus.NOT_EVALUATED
    login = logins[0] if logins else ()
    if ("no", "login") in children and login:
        return RuleStatus.NOT_EVALUATED
    if login == ("login", "local"):
        return RuleStatus.PASS if _local_secret_exists(blocks) else RuleStatus.NOT_EVALUATED
    if login[:2] == ("login", "authentication") or (aaa and not login):
        if not aaa or (login and len(login) != 3):
            return RuleStatus.NOT_EVALUATED
        name = login[2] if login else "default"
        methods = [item.head.tokens[4:] for item in blocks
                   if item.head.tokens[:4] == ("aaa", "authentication", "login", name)]
        if len(methods) != 1:
            return RuleStatus.NOT_EVALUATED
        if methods[0] == ("none",):
            return RuleStatus.FAIL
        if methods[0] in {("local",), ("local-case",)}:
            return RuleStatus.PASS if _local_secret_exists(blocks) else RuleStatus.NOT_EVALUATED
        return RuleStatus.NOT_EVALUATED
    if login == ("login",) and not aaa:
        passwords = [tokens[1:] for tokens in children if tokens[:1] == ("password",)]
        if len(passwords) == 1 and _secret_payload(passwords[0], {"0", "7"}):
            return RuleStatus.PASS
        return RuleStatus.NOT_EVALUATED if passwords else RuleStatus.FAIL
    if login or aaa or any(tokens[:1] == ("authentication",) for tokens in children):
        return RuleStatus.NOT_EVALUATED
    return RuleStatus.FAIL


@dataclass(frozen=True, slots=True)
class ConsoleAuthenticationRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-AUTH-002"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        blocks = _blocks(context)
        consoles = [block for block in blocks if block.head.tokens[:2] == ("line", "console")]
        states = [_console_state(block, blocks) if len(block.head.tokens) == 3
                  and block.head.tokens[2].isdigit() else RuleStatus.NOT_EVALUATED
                  for block in consoles]
        status = _aggregate(states)
        text = {
            RuleStatus.PASS: "consola: autenticación explícita configurada; valores redactados",
            RuleStatus.FAIL: "consola: autenticación ausente o explícitamente deshabilitada",
            RuleStatus.NOT_EVALUATED: "consola: mecanismo no determinable con la información disponible",
        }[status]
        index = states.index(status) if status in states else None
        return _result(self.metadata, context, status, text,
                       consoles[index].head.number if index is not None else None)


def _extended_number(value: str) -> bool:
    return value.isdigit() and (100 <= int(value) <= 199 or 2000 <= int(value) <= 2699)


def _endpoint(tokens: tuple[str, ...], index: int) -> tuple[int, bool] | None:
    if index >= len(tokens):
        return None
    if tokens[index] == "any":
        return index + 1, True
    try:
        if tokens[index] == "host" and index + 1 < len(tokens):
            IPv4Address(tokens[index + 1])
            return index + 2, False
        if index + 1 < len(tokens):
            IPv4Address(tokens[index])
            IPv4Address(tokens[index + 1])
            return index + 2, tokens[index + 1] == "255.255.255.255"
    except ValueError:
        return None
    return None


def _acl_entry(tokens: tuple[str, ...]) -> RuleStatus | None:
    if tokens and tokens[0].isdigit():
        tokens = tokens[1:]
    if tokens[:1] in {("remark",), ("no",)}:
        return None
    if len(tokens) < 4 or tokens[0] not in {"permit", "deny"}:
        return RuleStatus.NOT_EVALUATED
    if tokens[1] not in {"ip", "tcp", "udp", "icmp", "gre", "ospf", "esp", "ahp"}:
        return RuleStatus.NOT_EVALUATED
    source = _endpoint(tokens, 2)
    destination = _endpoint(tokens, source[0]) if source else None
    if source is None or destination is None:
        return RuleStatus.NOT_EVALUATED
    if tokens[destination[0]:] not in {(), ("log",), ("log-input",)}:
        return RuleStatus.NOT_EVALUATED
    if tokens[:2] == ("permit", "ip") and source[1] and destination[1]:
        return RuleStatus.FAIL
    return RuleStatus.PASS


@dataclass(frozen=True, slots=True)
class GlobalAclPermitRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-ACL-001"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        entries: list[tuple[RuleStatus, int]] = []
        present = False
        for block in _blocks(context):
            tokens = block.head.tokens
            if tokens[:3] == ("ip", "access-list", "extended"):
                present = True
                if len(tokens) != 4:
                    entries.append((RuleStatus.NOT_EVALUATED, block.head.number))
                    continue
                states = [(state, line.number) for line in block.children
                          if (state := _acl_entry(line.tokens)) is not None]
                entries.extend(states or [(RuleStatus.NOT_EVALUATED, block.head.number)])
            elif tokens[:1] == ("access-list",):
                if len(tokens) >= 2 and _extended_number(tokens[1]):
                    present = True
                    state = _acl_entry(tokens[2:])
                    if state is not None:
                        entries.append((state, block.head.number))
                elif len(tokens) < 2 or not tokens[1].isdigit():
                    present = True
                    entries.append((RuleStatus.NOT_EVALUATED, block.head.number))
            elif tokens[:2] == ("ip", "access-list") and tokens[2:3] != ("standard",):
                present = True
                entries.append((RuleStatus.NOT_EVALUATED, block.head.number))
        status = _aggregate([item[0] for item in entries]) if present else RuleStatus.NOT_APPLICABLE
        texts = {
            RuleStatus.FAIL: "ACL (identificador redactado): permit ip any any (permiso global)",
            RuleStatus.PASS: "ACL IPv4 extendida evaluable: sin permiso IP global any-any",
            RuleStatus.NOT_APPLICABLE: "ACL IPv4 extendida: no configurada dentro del alcance",
            RuleStatus.NOT_EVALUATED: "ACL IPv4 extendida: sintaxis o contenido insuficiente",
        }
        line = next((number for state, number in entries if state == status), None)
        return _result(self.metadata, context, status, texts[status], line)


def _area(value: str) -> int | None:
    try:
        result = int(value) if value.isdigit() else int(IPv4Address(value))
    except ValueError:
        return None
    return result if 0 <= result <= 4294967295 else None


def _process_id(value: str) -> bool:
    return value.isdigit() and 1 <= int(value) <= 65535


def _passive(interface: str, process: _Block) -> bool | None:
    children = [line.tokens for line in process.children]
    enabled = ("passive-interface", interface) in children
    disabled = ("no", "passive-interface", interface) in children
    if enabled and disabled:
        return None
    return enabled or (("passive-interface", "default") in children and not disabled)


def _ospf_authentication(interface: _Block, process: _Block, area: int) -> RuleStatus:
    commands = [line.tokens for line in interface.children]
    modes = [tokens[3:] for tokens in commands if tokens[:3] == ("ip", "ospf", "authentication")]
    negated = ("no", "ip", "ospf", "authentication") in commands
    if len(modes) > 1 or (modes and negated):
        return RuleStatus.NOT_EVALUATED
    if modes:
        mode = modes[0]
    else:
        inherited = [line.tokens[3:] for line in process.children
                     if len(line.tokens) >= 3 and line.tokens[0] == "area"
                     and _area(line.tokens[1]) == area and line.tokens[2] == "authentication"]
        if len(inherited) > 1:
            return RuleStatus.NOT_EVALUATED
        mode = inherited[0] if inherited else ("null",)
    if mode == ("null",):
        return RuleStatus.FAIL
    if mode == ():
        keys = [tokens[3:] for tokens in commands
                if tokens[:3] == ("ip", "ospf", "authentication-key")]
        return RuleStatus.PASS if len(keys) == 1 and _secret_payload(keys[0], {"0", "7"}) else RuleStatus.NOT_EVALUATED
    if mode == ("message-digest",):
        keys = [tokens[3:] for tokens in commands
                if tokens[:3] == ("ip", "ospf", "message-digest-key")]
        if any(len(key) >= 3 and key[0].isdigit() and 1 <= int(key[0]) <= 255
               and key[1] == "md5" and _secret_payload(key[2:], {"0", "7"}) for key in keys):
            return RuleStatus.PASS
    return RuleStatus.NOT_EVALUATED


def _ospf_states(blocks: tuple[_Block, ...]) -> list[tuple[RuleStatus, int]]:
    processes = [block for block in blocks if block.head.tokens[:2] == ("router", "ospf")]
    interfaces = [block for block in blocks if block.head.tokens[:1] == ("interface",)]
    results: list[tuple[RuleStatus, int]] = []
    for process in processes:
        if len(process.head.tokens) != 3 or not _process_id(process.head.tokens[2]):
            results.append((RuleStatus.NOT_EVALUATED, process.head.number))
            continue
        pid = process.head.tokens[2]
        if sum(block.head.tokens == process.head.tokens for block in processes) > 1:
            results.append((RuleStatus.NOT_EVALUATED, process.head.number))
            continue
        children = [line.tokens for line in process.children]
        # Network-based activation / virtual links require a richer topology model.
        ambiguous = any(tokens[:1] == ("network",) or "virtual-link" in tokens for tokens in children)
        bound = False
        for interface in interfaces:
            commands = [line.tokens for line in interface.children]
            bindings = [tokens for tokens in commands if tokens[:2] == ("ip", "ospf")
                        and len(tokens) >= 3 and tokens[2] == pid]
            if not bindings:
                continue
            bound = True
            passive = _passive(interface.head.tokens[1], process) if len(interface.head.tokens) == 2 else None
            if ("shutdown",) in commands or passive is True:
                results.append((RuleStatus.NOT_APPLICABLE, interface.head.number))
                continue
            addresses = [tokens[2:] for tokens in commands if tokens[:2] == ("ip", "address")]
            valid_address = False
            if len(addresses) == 1 and len(addresses[0]) == 2:
                try:
                    network = IPv4Network("/".join(addresses[0]), strict=False)
                    # IPv4Network also accepts hostmasks; IOS interface addresses
                    # require the actual contiguous netmask, not its inverse.
                    valid_address = str(network.netmask) == addresses[0][1]
                except ValueError:
                    pass
            binding = bindings[0]
            area = _area(binding[4]) if len(binding) == 5 and binding[3] == "area" else None
            other_bindings = [tokens for tokens in commands if len(tokens) >= 3
                              and tokens[:2] == ("ip", "ospf") and tokens[2].isdigit()]
            vrf = any(tokens[:3] == ("ip", "vrf", "forwarding") or
                      tokens[:2] == ("vrf", "forwarding") for tokens in commands)
            if len(other_bindings) != 1 or area is None or not valid_address or passive is None or vrf:
                state = RuleStatus.NOT_EVALUATED
            else:
                state = _ospf_authentication(interface, process, area)
            results.append((state, interface.head.number))
        if not bound or ambiguous:
            results.append((RuleStatus.NOT_EVALUATED, process.head.number))
    # A binding without its process cannot prove applicability/authentication.
    ids = {block.head.tokens[2] for block in processes if len(block.head.tokens) == 3}
    for interface in interfaces:
        if any(len(line.tokens) >= 3 and line.tokens[:2] == ("ip", "ospf")
               and line.tokens[2].isdigit() and line.tokens[2] not in ids for line in interface.children):
            results.append((RuleStatus.NOT_EVALUATED, interface.head.number))
    return results


@dataclass(frozen=True, slots=True)
class OspfAuthenticationRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-OSPF-001"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        states = _ospf_states(_blocks(context))
        applicable = [status for status, _ in states if status != RuleStatus.NOT_APPLICABLE]
        status = _aggregate(applicable) if applicable else RuleStatus.NOT_APPLICABLE
        texts = {
            RuleStatus.PASS: "OSPF: autenticación explícita y clave presente; valores redactados",
            RuleStatus.FAIL: "OSPF: interfaz aplicable con autenticación ausente o nula",
            RuleStatus.NOT_APPLICABLE: "OSPFv2: sin interfaz aplicable dentro del alcance",
            RuleStatus.NOT_EVALUATED: "OSPF: contexto o mecanismo de autenticación no determinable",
        }
        line = next((number for item, number in states if item == status), None)
        return _result(self.metadata, context, status, texts[status], line)


def _snmp_community(tokens: tuple[str, ...]) -> RuleStatus:
    if len(tokens) < 3:
        return RuleStatus.NOT_EVALUATED
    value = tokens[2]
    if value.isdigit() or value.startswith(('"', "'")):
        return RuleStatus.NOT_EVALUATED
    index = 3
    if tokens[index:index + 1] == ("view",):
        if index + 1 >= len(tokens):
            return RuleStatus.NOT_EVALUATED
        index += 2
    mode = "ro"  # Valor predeterminado documentado de Cisco IOS.
    if index < len(tokens):
        if tokens[index] not in {"RO", "RW", "ro", "rw"}:
            return RuleStatus.NOT_EVALUATED
        mode = tokens[index].casefold()
        if tokens[index + 1:index + 2] == ("ipv6",):
            return RuleStatus.NOT_EVALUATED
        if len(tokens) > index + 2:
            return RuleStatus.NOT_EVALUATED
    if value.casefold() in {"public", "private"} or mode == "rw":
        return RuleStatus.FAIL
    return RuleStatus.PASS


@dataclass(frozen=True, slots=True)
class SnmpCommunityRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-SNMP-001"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        roots = [block.head for block in _blocks(context)]
        communities = [line for line in roots if line.tokens[:2] == ("snmp-server", "community")]
        states = [_snmp_community(line.tokens) for line in communities]
        if communities:
            status = _aggregate(states)
        else:
            status = RuleStatus.NOT_EVALUATED if any(line.tokens[:1] == ("snmp-server",) for line in roots) else RuleStatus.NOT_APPLICABLE
        texts = {
            RuleStatus.PASS: "SNMP: comunidades RO no predeterminadas; valores redactados",
            RuleStatus.FAIL: "comunidad SNMP insegura detectada: valor redactado",
            RuleStatus.NOT_APPLICABLE: "SNMP: sin configuración activa",
            RuleStatus.NOT_EVALUATED: "SNMP: sintaxis o versión fuera del alcance evaluable",
        }
        index = states.index(status) if status in states else None
        return _result(self.metadata, context, status, texts[status],
                       communities[index].number if index is not None else None)


@dataclass(frozen=True, slots=True)
class HostnameRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-DOC-001"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        names = [block.head for block in _blocks(context) if block.head.tokens[:1] == ("hostname",)]
        if not names:
            return _result(self.metadata, context, RuleStatus.FAIL, "hostname: ausente")
        if len(names) != 1 or len(names[0].tokens) != 2 or re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,252}", names[0].tokens[1]
        ) is None:
            return _result(self.metadata, context, RuleStatus.NOT_EVALUATED,
                           "hostname: directiva ambigua o no reconocida", names[0].number)
        generic = names[0].tokens[1].casefold() in {"router", "switch"}
        return _result(self.metadata, context, RuleStatus.FAIL if generic else RuleStatus.PASS,
                       "hostname genérico detectado" if generic else "hostname explícito no genérico",
                       names[0].number)
