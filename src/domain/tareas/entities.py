"""Entidades de dominio para el subdominio de tareas (To-Do List)."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from src.domain.tareas.exceptions import TareaInvalidaException
from src.domain.tareas.value_objects import (
    CategoriaTarea,
    EstadoTarea,
    PrioridadTarea,
)


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Tarea:
    id_tarea: str
    titulo: str
    descripcion: str = ""
    fecha_limite: date | None = None
    prioridad: PrioridadTarea = PrioridadTarea.MEDIA
    estado: EstadoTarea = EstadoTarea.PENDIENTE
    categoria: CategoriaTarea = CategoriaTarea.GENERAL
    docente_cuit: str | None = None
    id_referencia: str | None = None
    tipo_referencia: str | None = None
    fecha_creacion: datetime = field(default_factory=_ahora_utc)
    fecha_completada: datetime | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadatos: dict[str, Any] = field(default_factory=dict[str, Any])

    def __post_init__(self) -> None:
        if not self.id_tarea or not self.id_tarea.strip():
            raise TareaInvalidaException("El ID de la tarea no puede estar vacío.")
        if not self.titulo or not self.titulo.strip():
            raise TareaInvalidaException("El título de la tarea no puede estar vacío.")
        if len(self.titulo.strip()) > 250:
            raise TareaInvalidaException(
                "El título no puede exceder los 250 caracteres."
            )
        if self.docente_cuit is not None:
            cuit_clean = self.docente_cuit.replace("-", "").strip()
            object.__setattr__(self, "docente_cuit", cuit_clean if cuit_clean else None)

    def completar(self, fecha: datetime | None = None) -> "Tarea":
        """Retorna una nueva instancia de la tarea marcada como COMPLETADA."""
        fecha_comp = fecha or _ahora_utc()
        return Tarea(
            id_tarea=self.id_tarea,
            titulo=self.titulo,
            descripcion=self.descripcion,
            fecha_limite=self.fecha_limite,
            prioridad=self.prioridad,
            estado=EstadoTarea.COMPLETADA,
            categoria=self.categoria,
            docente_cuit=self.docente_cuit,
            id_referencia=self.id_referencia,
            tipo_referencia=self.tipo_referencia,
            fecha_creacion=self.fecha_creacion,
            fecha_completada=fecha_comp,
            tags=self.tags,
            metadatos=dict(self.metadatos),
        )
