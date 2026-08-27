"""Caso de uso para auditar y validar la compatibilidad de horarios docentes."""

from src.application.dtos.horarios_docencia_dto import (
    DeclaracionHorariaInputDTO,
    ResultadoCompatibilidadDTO,
)
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.services import ValidadorHorariosDocenciaService


class ValidarHorariosDocenciaUseCase:
    """Orquesta la validación de una declaración horaria docente."""

    def __init__(
        self,
        validador_service: ValidadorHorariosDocenciaService | None = None,
    ) -> None:
        self._validador = (
            validador_service
            if validador_service is not None
            else ValidadorHorariosDocenciaService()
        )

    def execute(
        self, input_dto: DeclaracionHorariaInputDTO
    ) -> ResultadoCompatibilidadDTO:
        """Ejecuta el análisis de superposiciones, traslados y topes estatutarios."""
        declaracion_dominio = HorariosDocenciaMapper.to_domain(input_dto)
        resultado_dominio = self._validador.validar(
            declaracion=declaracion_dominio,
            margen_traslado_minutos=input_dto.margen_traslado_minutos,
        )
        return HorariosDocenciaMapper.to_dto(resultado_dominio)
