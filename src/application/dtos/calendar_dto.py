"""Pydantic v2 DTOs for calendar and appointments bounded context."""

from datetime import datetime

from pydantic import BaseModel, Field


class CalendarEventDTO(BaseModel):
    """Output DTO for a calendar event."""

    id_evento: str
    id_calendario: str
    uid: str
    titulo: str
    inicio: datetime
    fin: datetime
    descripcion: str = ""
    ubicacion: str = ""
    todo_el_dia: bool = False
    estado: str = "CONFIRMED"
    asistentes: list[str] = Field(default_factory=list[str])
    url: str = ""
    categorias: str = ""
    cuenta: str = ""


class CreateEventDTO(BaseModel):
    """Input DTO for creating a new calendar event."""

    titulo: str = Field(..., description="Título del evento o reunión")
    inicio: datetime = Field(..., description="Fecha y hora de inicio (ISO 8601)")
    fin: datetime = Field(..., description="Fecha y hora de fin (ISO 8601)")
    descripcion: str = Field(default="", description="Descripción detallada")
    ubicacion: str = Field(default="", description="Lugar físico o enlace de reunión")
    todo_el_dia: bool = Field(default=False, description="Evento de día completo")
    asistentes: list[str] = Field(
        default_factory=list[str], description="Lista de correos de asistentes"
    )
    url: str = Field(default="", description="URL externa o de videollamada")
    categorias: str = Field(default="", description="Categorías / etiquetas")
    cuenta: str | None = Field(
        default=None, description="Cuenta de correo asociada (opcional)"
    )


class UpdateEventDTO(BaseModel):
    """Input DTO for modifying an existing calendar event."""

    titulo: str | None = Field(default=None, description="Título del evento")
    inicio: datetime | None = Field(default=None, description="Fecha y hora de inicio")
    fin: datetime | None = Field(default=None, description="Fecha y hora de fin")
    descripcion: str | None = Field(default=None, description="Descripción")
    ubicacion: str | None = Field(default=None, description="Ubicación")
    todo_el_dia: bool | None = Field(default=None, description="Día completo")
    estado: str | None = Field(
        default=None, description="CONFIRMED, TENTATIVE, CANCELLED"
    )
    asistentes: list[str] | None = Field(default=None, description="Asistentes")
    url: str | None = Field(default=None, description="URL")
    categorias: str | None = Field(default=None, description="Categorías")
    cuenta: str | None = Field(default=None, description="Cuenta asociada")


class TimeSlotDTO(BaseModel):
    """Output DTO for a time slot availability block."""

    inicio: datetime
    fin: datetime
    disponible: bool
    motivo: str = ""


class AvailabilityResponseDTO(BaseModel):
    """Output DTO for schedule availability check."""

    fecha: str
    cuenta: str
    duracion_minutos: int
    bloques: list[TimeSlotDTO] = Field(default_factory=list[TimeSlotDTO])
