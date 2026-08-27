"""Controlador agnóstico de frameworks web para horarios de docencia y compatibilidad."""

from src.application.dtos.horarios_docencia_dto import (
    DeclaracionHorariaInputDTO,
    ResultadoCompatibilidadDTO,
)
from src.application.use_cases.validar_horarios_docencia import (
    ValidarHorariosDocenciaUseCase,
)


class HorariosDocenciaController:
    """Controlador puro de aplicación para la gestión y auditoría de horarios docentes."""

    def __init__(
        self,
        validar_use_case: ValidarHorariosDocenciaUseCase | None = None,
    ) -> None:
        self._validar_use_case = (
            validar_use_case
            if validar_use_case is not None
            else ValidarHorariosDocenciaUseCase()
        )

    def validar_declaracion(
        self,
        input_dto: DeclaracionHorariaInputDTO,
    ) -> ResultadoCompatibilidadDTO:
        """Audita una declaración horaria y retorna el reporte de compatibilidad."""
        return self._validar_use_case.execute(input_dto)
