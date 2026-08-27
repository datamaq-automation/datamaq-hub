"""Caso de uso para registrar una nueva designación o suplencia docente con vigencia temporal."""

from src.application.dtos.horarios_docencia_dto import (
    DesignacionDocenteDTO,
    RegistrarDesignacionInputDTO,
)
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort


class RegistrarDesignacionUseCase:
    """Orquesta el registro inmutable de una designación docente."""

    def __init__(self, repository: DesignacionDocenteRepositoryPort) -> None:
        self._repository = repository

    def execute(self, input_dto: RegistrarDesignacionInputDTO) -> DesignacionDocenteDTO:
        """Persiste la designación y retorna su representación DTO."""
        designacion_domain = HorariosDocenciaMapper.to_designacion_domain(input_dto)
        guardada = self._repository.guardar(designacion_domain)
        return HorariosDocenciaMapper.designacion_to_dto(guardada)
