"""Caso de uso para finalizar la vigencia de una designación o suplencia docente."""

from datetime import date

from src.application.dtos.horarios_docencia_dto import (
    CesarDesignacionInputDTO,
    DesignacionDocenteDTO,
)
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import MotivoCese


class CesarDesignacionUseCase:
    """Orquesta el cese o fin de vigencia de una designación sin borrado destructivo."""

    def __init__(self, repository: DesignacionDocenteRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self, id_designacion: str, input_dto: CesarDesignacionInputDTO
    ) -> DesignacionDocenteDTO | None:
        """Sella la fecha de fin y motivo de cese de la designación."""
        f_hasta = date.fromisoformat(input_dto.fecha_hasta.strip())
        motivo_str = input_dto.motivo_cese.strip().upper()
        motivo_enum = (
            MotivoCese[motivo_str]
            if motivo_str in MotivoCese.__members__
            else MotivoCese.FIN_SUPLENCIA
        )

        actualizada = self._repository.cerrar_vigencia(
            id_designacion=id_designacion.strip(),
            fecha_hasta=f_hasta,
            motivo=motivo_enum,
        )
        return (
            HorariosDocenciaMapper.designacion_to_dto(actualizada)
            if actualizada
            else None
        )
