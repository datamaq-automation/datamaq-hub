"""Caso de uso para consultar la línea de tiempo histórica completa de designaciones de un docente."""

from src.application.dtos.horarios_docencia_dto import DesignacionDocenteDTO
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import normalizar_cuit


class ConsultarHistorialDocenteUseCase:
    """Recupera el historial completo de designaciones, titulares y suplencias."""

    def __init__(self, repository: DesignacionDocenteRepositoryPort) -> None:
        self._repository = repository

    def execute(self, docente_cuit: str) -> list[DesignacionDocenteDTO]:
        """Retorna la lista ordenada cronológicamente de designaciones históricas."""
        clean_cuit = normalizar_cuit(docente_cuit)
        historial = self._repository.obtener_historial(docente_cuit=clean_cuit)
        return [HorariosDocenciaMapper.designacion_to_dto(d) for d in historial]
