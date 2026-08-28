"""Domain value objects for leads bounded context."""

from dataclasses import dataclass
from enum import Enum


class LeadStatus(str, Enum):
    """Lifecycle status of a prospective client lead."""

    NUEVO = "NUEVO"
    EN_SEGUIMIENTO = "EN_SEGUIMIENTO"
    CONTACTADO = "CONTACTADO"
    CONVERTIDO = "CONVERTIDO"
    DESCARTADO = "DESCARTADO"


@dataclass(frozen=True)
class LeadSourceInfo:
    """Immutable value object capturing source channel and UTM campaign."""

    channel: str = "web"
    campaign: str = ""
    medium: str = ""
    term: str = ""
