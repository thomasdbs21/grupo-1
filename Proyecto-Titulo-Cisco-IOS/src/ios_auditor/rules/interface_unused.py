"""Sin uso declarado y corroborado, nunca inferido solamente desde down/down."""

import re

from ios_auditor.domain.models import MultiSourceContext, RuleStatus
from ios_auditor.domain.operational_sources import ShowInterfacesData
from ios_auditor.rules.evaluation2 import _blocks

PASS, FAIL, NA, NE = (RuleStatus.PASS, RuleStatus.FAIL,
                      RuleStatus.NOT_APPLICABLE, RuleStatus.NOT_EVALUATED)
# Policy marker, not a Cisco keyword or an automatic inventory inference.
UNUSED_DESCRIPTION = ("description", "NETAUDIT_UNUSED")
_PHYSICAL = re.compile(r"(?:Ethernet|FastEthernet|GigabitEthernet|TenGigabitEthernet|TwentyFiveGigE|FortyGigabitEthernet|HundredGigE)\d+(?:/\d+)*")
_EXCLUDED = re.compile(r"(?:Loopback|Tunnel|Vlan|Port-channel|BDI|Null|Virtual-Access|Virtual-Template)\d+(?:\.\d+)?")


def _kind(name: str) -> str:
    if _PHYSICAL.fullmatch(name):
        return "physical"
    if (_EXCLUDED.fullmatch(name) or "." in name
            and _PHYSICAL.fullmatch(name.split(".")[0]) and name.split(".")[1].isdigit()):
        return "excluded"
    return "unknown"


def unused_interface_status(context: MultiSourceContext) -> RuleStatus:
    source = next((item for item in context.operational
                   if item.command == "show interfaces" and isinstance(item.data, ShowInterfacesData)), None)
    if source is None or not source.data.recognized:
        return NE
    blocks = [block for block in _blocks(context.configuration)
              if block.head.tokens[:1] == ("interface",)]
    if any(len(block.head.tokens) != 2 for block in blocks):
        return NE
    names = [item.name for item in source.data.interfaces]
    if len(names) != len(set(names)):
        return NE
    states = []
    for item in source.data.interfaces:
        kind = _kind(item.name)
        if kind == "excluded":
            continue
        matches = [block for block in blocks if block.head.tokens == ("interface", item.name)]
        if kind == "unknown" or len(matches) != 1:
            states.append(NE)
            continue
        children = tuple(line.tokens for line in matches[0].children)
        admin = [tokens for tokens in children if tokens[:1] == ("shutdown",)
                 or tokens[:2] == ("no", "shutdown")]
        descriptions = [tokens for tokens in children if tokens[:1] == ("description",)
                        or tokens[:2] == ("no", "description")]
        if (len(admin) > 1 or any(tokens not in {("shutdown",), ("no", "shutdown")} for tokens in admin)
                or len(descriptions) > 1):
            states.append(NE)
        elif (item.status, item.protocol) == ("administratively down", "down"):
            states.append(NE if ("no", "shutdown") in admin else PASS)
        elif (item.status, item.protocol) == ("up", "up"):
            states.append(NE if ("shutdown",) in admin else PASS)
        elif (item.status, item.protocol) != ("down", "down") or ("shutdown",) in admin:
            states.append(NE)
        elif (descriptions == [UNUSED_DESCRIPTION] and admin == [("no", "shutdown")]
              and item.input_packets == item.output_packets == item.input_errors == item.output_errors == 0):
            states.append(FAIL)
        else:
            states.append(NE)
    # Missing physical interfaces cannot silently vanish from the audit.
    if any(_kind(block.head.tokens[1]) != "excluded" and block.head.tokens[1] not in names for block in blocks):
        states.append(NE)
    return FAIL if FAIL in states else NE if NE in states else PASS if states else NA
