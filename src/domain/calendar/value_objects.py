"""Value objects for calendar domain."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.domain.calendar.exceptions import InvalidEventDataError


class EventStatus(str, Enum):
    """Status of calendar event."""

    CONFIRMED = "CONFIRMED"
    TENTATIVE = "TENTATIVE"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class EventId:
    """Immutable identifier for calendar events."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not str(self.value).strip():
            raise InvalidEventDataError(
                "El identificador del evento no puede estar vacío."
            )
        object.__setattr__(self, "value", str(self.value).strip())


@dataclass(frozen=True)
class EventDateTimeInterval:
    """Immutable start and end timestamp interval."""

    inicio: datetime
    fin: datetime

    def __post_init__(self) -> None:
        if self.inicio > self.fin:
            raise InvalidEventDataError(
                f"La fecha de inicio ({self.inicio}) no puede ser posterior a la fecha de fin ({self.fin})."
            )

    @property
    def duracion_segundos(self) -> float:
        return (self.fin - self.inicio).total_seconds()

    @property
    def duracion_minutos(self) -> float:
        return self.duracion_segundos / 60.0
