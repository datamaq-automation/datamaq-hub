"""Mappers para el subdominio de tareas."""

import uuid

from src.application.dtos.tarea_dtos import CrearTareaDTO, TareaResponseDTO
from src.domain.tareas.entities import Tarea


class TareaMapper:
    """Conversor entre entidades de dominio Tarea y DTOs."""

    @staticmethod
    def to_dto(entity: Tarea) -> TareaResponseDTO:
        return TareaResponseDTO(
            id_tarea=entity.id_tarea,
            titulo=entity.titulo,
            descripcion=entity.descripcion,
            fecha_limite=entity.fecha_limite,
            prioridad=entity.prioridad,
            estado=entity.estado,
            categoria=entity.categoria,
            docente_cuit=entity.docente_cuit,
            id_referencia=entity.id_referencia,
            tipo_referencia=entity.tipo_referencia,
            fecha_creacion=entity.fecha_creacion,
            fecha_completada=entity.fecha_completada,
            tags=list(entity.tags),
            metadatos=dict(entity.metadatos),
        )

    @staticmethod
    def to_domain_from_create(dto: CrearTareaDTO, id_tarea: str | None = None) -> Tarea:
        return Tarea(
            id_tarea=id_tarea or str(uuid.uuid4()),
            titulo=dto.titulo.strip(),
            descripcion=dto.descripcion.strip(),
            fecha_limite=dto.fecha_limite,
            prioridad=dto.prioridad,
            categoria=dto.categoria,
            docente_cuit=dto.docente_cuit,
            id_referencia=dto.id_referencia,
            tipo_referencia=dto.tipo_referencia,
            tags=tuple(dto.tags),
            metadatos=dict(dto.metadatos),
        )
