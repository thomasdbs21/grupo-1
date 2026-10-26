"""Datos mínimos inmutables; las direcciones de NTP/vecinos no se conservan."""

from dataclasses import dataclass


def _freeze_records(owner: object, field: str, expected: type) -> None:
    entries = tuple(getattr(owner, field))
    if not all(isinstance(item, expected) for item in entries):
        raise TypeError("Los registros operacionales son incompatibles.")
    if type(getattr(owner, "recognized")) is not bool:
        raise TypeError("El indicador de formato debe ser booleano.")
    object.__setattr__(owner, field, entries)


@dataclass(frozen=True, slots=True)
class InterfaceCounters:
    name: str
    status: str
    protocol: str
    input_packets: int | None
    input_errors: int | None
    output_packets: int | None
    output_errors: int | None


@dataclass(frozen=True, slots=True)
class ShowInterfacesData:
    interfaces: tuple[InterfaceCounters, ...] = ()
    recognized: bool = False

    def __post_init__(self) -> None:
        _freeze_records(self, "interfaces", InterfaceCounters)


@dataclass(frozen=True, slots=True)
class AccessListEntry:
    name: str
    kind: str


@dataclass(frozen=True, slots=True)
class ShowAccessListsData:
    access_lists: tuple[AccessListEntry, ...] = ()
    recognized: bool = False

    def __post_init__(self) -> None:
        _freeze_records(self, "access_lists", AccessListEntry)


@dataclass(frozen=True, slots=True)
class NtpAssociation:
    synchronized: bool
    stratum: int
    reach: int


@dataclass(frozen=True, slots=True)
class ShowNtpAssociationsData:
    associations: tuple[NtpAssociation, ...] = ()
    recognized: bool = False

    def __post_init__(self) -> None:
        _freeze_records(self, "associations", NtpAssociation)


@dataclass(frozen=True, slots=True)
class OspfNeighbor:
    state: str
    role: str
    interface: str


@dataclass(frozen=True, slots=True)
class ShowIpOspfNeighborData:
    neighbors: tuple[OspfNeighbor, ...] = ()
    recognized: bool = False

    def __post_init__(self) -> None:
        _freeze_records(self, "neighbors", OspfNeighbor)
