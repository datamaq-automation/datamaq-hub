"""Domain entities for leads bounded context."""

from dataclasses import dataclass, field

from src.domain.leads.value_objects import LeadSourceInfo, LeadStatus


@dataclass(frozen=True)
class Lead:
    """Immutable entity representing a commercial business lead."""

    id_lead: str
    nombre: str
    email: str
    telefono: str = ""
    empresa: str = ""
    mensaje: str = ""
    fuente: LeadSourceInfo = field(default_factory=LeadSourceInfo)
    estado: LeadStatus = LeadStatus.NUEVO
    fecha_creacion: str = ""
