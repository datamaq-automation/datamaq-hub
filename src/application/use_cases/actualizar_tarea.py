"""Caso de uso para actualizar los datos de una tarea existente."""

from datetime import datetime, timezone

from src.application.dtos.tarea_dtos import ActualizarTareaDTO, TareaResponseDTO
from src.application.mappers.tarea_mapper import TareaMapper
from src.domain.tareas.entities import Tarea
from src.domain.tareas.exceptions import TareaNoEncontradaException
from src.domain.tareas.ports import TareaRepositoryPort
from src.domain.tareas.value_objects import EstadoTarea


class ActualizarTareaUseCase:
    """Modifica los campos de una tarea existente."""

    def __init__(self, repository: TareaRepositoryPort) -> None:
        self._repository = repository

    def execute(self, id_tarea: str, dto: ActualizarTareaDTO) -> TareaResponseDTO:
        existente = self._repository.obtener_por_id(id_tarea)
        if not existente:
            raise TareaNoEncontradaException(
                f"No se encontró la tarea con ID '{id_tarea}'."
            )

        nuevo_estado = dto.estado if dto.estado is not None else existente.estado
        fecha_comp = existente.fecha_completada
        if (
            nuevo_estado == EstadoTarea.COMPLETADA
            and existente.estado != EstadoTarea.COMPLETADA
        ):
            fecha_comp = datetime.now(timezone.utc)
        elif nuevo_estado != EstadoTarea.COMPLETADA:
            fecha_comp = None

        nuevos_meta = dict(existente.metadatos)
        if dto.metadatos is not None:
            nuevos_meta.update(dto.metadatos)

        actualizada = Tarea(
            id_tarea=existente.id_tarea,
            titulo=dto.titulo.strip() if dto.titulo is not None else existente.titulo,
            descripcion=dto.descripcion.strip()
            if dto.descripcion is not None
            else existente.descripcion,
            fecha_limite=dto.fecha_limite
            if dto.fecha_limite is not None
            else existente.fecha_limite,
            prioridad=dto.prioridad
            if dto.prioridad is not None
            else existente.prioridad,
            estado=nuevo_estado,
            categoria=dto.categoria
            if dto.categoria is not None
            else existente.categoria,
            docente_cuit=dto.docente_cuit
            if dto.docente_cuit is not None
            else existente.docente_cuit,
            id_referencia=dto.id_referencia
            if dto.id_referencia is not None
            else existente.id_referencia,
            tipo_referencia=dto.tipo_referencia
            if dto.tipo_referencia is not None
            else existente.tipo_referencia,
            fecha_creacion=existente.fecha_creacion,
            fecha_completada=fecha_comp,
            tags=tuple(dto.tags) if dto.tags is not None else existente.tags,
            metadatos=nuevos_meta,
        )

        guardada = self._repository.actualizar(actualizada)
        return TareaMapper.to_dto(guardada)
