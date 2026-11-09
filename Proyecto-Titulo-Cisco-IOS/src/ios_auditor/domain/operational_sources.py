"""Datos mínimos inmutables; las direcciones de NTP/vecinos no se conservan."""

from dataclasses import dataclass


# Fija la colección de registros para evitar modificaciones posteriores del contexto.
def _freeze_records(owner: object, field: str, expected: type) -> None:
    entries = tuple(getattr(owner, field))
    if not all(isinstance(item, expected) for item in entries):
        raise TypeError("Los registros operacionales son incompatibles.")
    if type(getattr(owner, "recognized")) is not bool:
        raise TypeError("El indicador de formato debe ser booleano.")
    object.__setattr__(owner, field, entries)


# Estado y contadores acumulados de una interfaz de show interfaces.
@dataclass(frozen=True, slots=True)
class InterfaceCounters:
    name: str
    status: str
    protocol: str
    input_packets: int | None
    input_errors: int | None
    output_packets: int | None
    output_errors: int | None


# Colección de interfaces con indicador de reconocimiento del formato.
@dataclass(frozen=True, slots=True)
class ShowInterfacesData:
    interfaces: tuple[InterfaceCounters, ...] = ()
    recognized: bool = False

    def __post_init__(self) -> None:
        _freeze_records(self, "interfaces", InterfaceCounters)


# Identidad y tipo de una ACL observada operacionalmente.
@dataclass(frozen=True, slots=True)
class AccessListEntry:
    name: str
    kind: str


# ACL reconocidas en la salida operacional para contrastarlas con la configuración.
@dataclass(frozen=True, slots=True)
class ShowAccessListsData:
    access_lists: tuple[AccessListEntry, ...] = ()
    recognized: bool = False

    def __post_init__(self) -> None:
        _freeze_records(self, "access_lists", AccessListEntry)


# Estado de sincronización y alcance de una asociación NTP.
@dataclass(frozen=True, slots=True)
class NtpAssociation:
    synchronized: bool
    stratum: int
    reach: int


# Tabla NTP normalizada con reconocimiento explícito del formato.
@dataclass(frozen=True, slots=True)
class ShowNtpAssociationsData:
    associations: tuple[NtpAssociation, ...] = ()
    recognized: bool = False

    def __post_init__(self) -> None:
        _freeze_records(self, "associations", NtpAssociation)


# Estado y rol de una vecindad OSPF observada.
@dataclass(frozen=True, slots=True)
class OspfNeighbor:
    state: str
    role: str
    interface: str


# Conjunto de vecinos observados, sin presuponer la topología esperada.
@dataclass(frozen=True, slots=True)
class ShowIpOspfNeighborData:
    neighbors: tuple[OspfNeighbor, ...] = ()
    recognized: bool = False

    def __post_init__(self) -> None:
        _freeze_records(self, "neighbors", OspfNeighbor)
