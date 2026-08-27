"""Pydantic v2 DTOs for teaching schedule and calendar synchronization."""

from datetime import date

from pydantic import BaseModel, Field

from src.application.dtos.calendar_dto import CalendarEventDTO


class SincronizarDocenciaDTO(BaseModel):
    """Input DTO for synchronizing teaching positions into calendar events."""

    cuit: str = Field(..., description="CUIT del docente (11 dígitos)")
    fecha_desde: date = Field(
        ..., description="Fecha inicial del intervalo a sincronizar"
    )
    fecha_hasta: date = Field(
        ..., description="Fecha final del intervalo a sincronizar"
    )
    limpiar_previos: bool = Field(
        default=True,
        description="Eliminar eventos de docencia previos en el rango para evitar duplicados",
    )
    account: str | None = Field(
        default=None, description="Cuenta de correo asociada (opcional)"
    )


class SincronizacionDocenteResponseDTO(BaseModel):
    """Output DTO summarizing synchronized teaching events."""

    cuit: str
    cuenta: str
    fecha_desde: date
    fecha_hasta: date
    total_eventos_creados: int
    eventos: list[CalendarEventDTO] = Field(default_factory=list[CalendarEventDTO])
