"""Builders acotados para TextFSM; no preservan destinos de NTP/OSPF."""

from ipaddress import IPv4Address
from types import MappingProxyType

from ios_auditor.domain.operational_sources import (
    AccessListEntry, InterfaceCounters, NtpAssociation, OspfNeighbor,
    ShowAccessListsData, ShowInterfacesData, ShowIpOspfNeighborData,
    ShowNtpAssociationsData,
)

NEW_SHOW_MODELS = MappingProxyType({
    "show interfaces": ShowInterfacesData,
    "show access-lists": ShowAccessListsData,
    "show ntp associations": ShowNtpAssociationsData,
    "show ip ospf neighbor": ShowIpOspfNeighborData,
})


def _counter(value: str) -> int | None:
    return int(value) if value else None


def build_operational_show(
    command: str, rows: tuple[dict[str, str], ...]
) -> ShowInterfacesData | ShowAccessListsData | ShowNtpAssociationsData | ShowIpOspfNeighborData:
    """Formato inválido se representa explícitamente, nunca como cumplimiento."""
    try:
        if command == "show interfaces":
            if not rows or len({row["NAME"] for row in rows}) != len(rows):
                return ShowInterfacesData()
            return ShowInterfacesData(tuple(
                InterfaceCounters(row["NAME"], row["STATUS"], row["PROTOCOL"],
                                  *(_counter(row[field]) for field in (
                                      "INPUT_PACKETS", "INPUT_ERRORS",
                                      "OUTPUT_PACKETS", "OUTPUT_ERRORS")))
                for row in rows
            ), True)
        if command == "show access-lists":
            if not rows or len({row["NAME"] for row in rows}) != len(rows):
                return ShowAccessListsData()
            return ShowAccessListsData(tuple(
                AccessListEntry(row["NAME"], row["KIND"].lower()) for row in rows
            ), True)
        if not rows or rows[0]["HEADER"] == "":
            return NEW_SHOW_MODELS[command]()
        entries = rows[1:]
        if command == "show ntp associations":
            values = []
            for row in entries:
                stratum, reach = int(row["STRATUM"]), int(row["REACH"], 8)
                if not 0 <= stratum <= 16 or not 0 <= reach <= 255:
                    return ShowNtpAssociationsData()
                values.append(NtpAssociation("*" in row["MARK"], stratum, reach))
            return ShowNtpAssociationsData(tuple(values), True)
        neighbors = []
        for row in entries:
            IPv4Address(row["NEIGHBOR"])
            IPv4Address(row["ADDRESS"])
            neighbors.append(OspfNeighbor(row["STATE"], row["ROLE"], row["INTERFACE"]))
        return ShowIpOspfNeighborData(tuple(neighbors), True)
    except (ValueError, KeyError):
        return NEW_SHOW_MODELS[command]()
