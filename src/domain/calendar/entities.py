"""Domain entities for calendar and appointments bounded context."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CalendarEvent:
    """Immutable entity representing an appointment or meeting on the calendar."""

    id_evento: str
    inicio: datetime
    fin: datetime
    titulo: str
    id_calendario: str = "1"
    uid: str = ""
    descripcion: str = ""
    ubicacion: str = ""
    todo_el_dia: bool = False
    estado: str = "CONFIRMED"
    asistentes: list[str] = field(default_factory=list[str])
    url: str = ""
    categorias: str = ""
    cuenta: str = ""


@dataclass(frozen=True)
class Calendar:
    """Immutable entity representing a calendar collection."""

    id_calendario: str
    nombre: str
    color: str = "#0288D1"
    cuenta: str = ""


@dataclass(frozen=True)
class TimeSlot:
    """Immutable block of time evaluated for schedule availability."""

    inicio: datetime
    fin: datetime
    disponible: bool = True
    motivo: str = ""
