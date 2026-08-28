"""DTOs de Pydantic v2 para el subdominio de tareas."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.tareas.value_objects import (
    CategoriaTarea,
    EstadoTarea,
    PrioridadTarea,
)


class TareaResponseDTO(BaseModel):
    """DTO de salida para una tarea."""

    id_tarea: str
    titulo: str
    descripcion: str = ""
    fecha_limite: date | None = None
    prioridad: PrioridadTarea
    estado: EstadoTarea
    categoria: CategoriaTarea
    docente_cuit: str | None = None
    id_referencia: str | None = None
    tipo_referencia: str | None = None
    fecha_creacion: datetime
    fecha_completada: datetime | None = None
    tags: list[str] = Field(default_factory=list[str])
    metadatos: dict[str, Any] = Field(default_factory=dict[str, Any])


class CrearTareaDTO(BaseModel):
    """DTO de entrada para crear una nueva tarea."""

    titulo: str = Field(
        ..., min_length=1, max_length=250, description="Título de la tarea"
    )
    descripcion: str = Field(default="", description="Descripción detallada")
    fecha_limite: date | None = Field(
        default=None, description="Fecha límite de vencimiento (YYYY-MM-DD)"
    )
    prioridad: PrioridadTarea = Field(
        default=PrioridadTarea.MEDIA,
        description="Prioridad: BAJA, MEDIA, ALTA, URGENTE",
    )
    categoria: CategoriaTarea = Field(
        default=CategoriaTarea.GENERAL,
        description="Categoría: DOCENCIA, RECIBOS, LEADS, CALENDARIO, GENERAL",
    )
    docente_cuit: str | None = Field(
        default=None, description="CUIT del docente asociado (opcional)"
    )
    id_referencia: str | None = Field(
        default=None, description="ID del objeto relacionado (ej. id_recibo)"
    )
    tipo_referencia: str | None = Field(
        default=None, description="Tipo de referencia (ej. RECIBO, DESIGNACION)"
    )
    tags: list[str] = Field(
        default_factory=list[str], description="Etiquetas de búsqueda"
    )
    metadatos: dict[str, Any] = Field(
        default_factory=dict[str, Any], description="Metadatos arbitrarios"
    )


class ActualizarTareaDTO(BaseModel):
    """DTO de entrada para actualizar una tarea existente."""

    titulo: str | None = Field(default=None, min_length=1, max_length=250)
    descripcion: str | None = Field(default=None)
    fecha_limite: date | None = Field(default=None)
    prioridad: PrioridadTarea | None = Field(default=None)
    estado: EstadoTarea | None = Field(default=None)
    categoria: CategoriaTarea | None = Field(default=None)
    docente_cuit: str | None = Field(default=None)
    id_referencia: str | None = Field(default=None)
    tipo_referencia: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    metadatos: dict[str, Any] | None = Field(default=None)


class ListarTareasResponseDTO(BaseModel):
    """DTO de respuesta para el listado paginado de tareas."""

    total: int
    tareas: list[TareaResponseDTO] = Field(default_factory=list[TareaResponseDTO])


class GenerarTareasReciboResponseDTO(BaseModel):
    """DTO de respuesta al auto-generar tareas desde un recibo."""

    id_recibo: str
    total_generadas: int
    tareas: list[TareaResponseDTO] = Field(default_factory=list[TareaResponseDTO])
