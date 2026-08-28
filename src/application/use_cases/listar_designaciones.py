"""Caso de uso para listar designaciones docentes con filtros y paginación."""

from datetime import date

from src.application.dtos.horarios_docencia_dto import DesignacionDocenteDTO
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import normalizar_cuit


class ListarDesignacionesUseCase:
    """Orquesta la consulta y filtrado de designaciones docentes."""

    def __init__(self, repository: DesignacionDocenteRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        cuit: str | None = None,
        vigentes_al: date | None = None,
        establecimiento: str | None = None,
        distrito: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DesignacionDocenteDTO]:
        """Recupera la lista de designaciones según los filtros proporcionados."""
        clean_cuit = normalizar_cuit(cuit) if cuit else None
        results = self._repository.listar(
            docente_cuit=clean_cuit,
            vigentes_al=vigentes_al,
            establecimiento=establecimiento.strip() if establecimiento else None,
            distrito=distrito.strip() if distrito else None,
            limit=limit,
            offset=offset,
        )
        return [HorariosDocenciaMapper.designacion_to_dto(d) for d in results]
