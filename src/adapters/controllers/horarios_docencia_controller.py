"""Controlador agnóstico de frameworks web para horarios de docencia y persistencia temporal."""

from datetime import date

from src.application.dtos.horarios_docencia_dto import (
    CesarDesignacionInputDTO,
    DeclaracionHorariaInputDTO,
    DesignacionDocenteDTO,
    RegistrarDesignacionInputDTO,
    ResultadoCompatibilidadDTO,
)
from src.application.use_cases.cesar_designacion import CesarDesignacionUseCase
from src.application.use_cases.consultar_designaciones_vigentes import (
    ConsultarDesignacionesVigentesUseCase,
)
from src.application.use_cases.consultar_historial_docente import (
    ConsultarHistorialDocenteUseCase,
)
from src.application.use_cases.registrar_designacion import RegistrarDesignacionUseCase
from src.application.use_cases.validar_horarios_docencia import (
    ValidarHorariosDocenciaUseCase,
)


class HorariosDocenciaController:
    """Controlador puro de aplicación para la gestión y auditoría temporal de horarios docentes."""

    def __init__(
        self,
        validar_use_case: ValidarHorariosDocenciaUseCase | None = None,
        registrar_use_case: RegistrarDesignacionUseCase | None = None,
        cesar_use_case: CesarDesignacionUseCase | None = None,
        consultar_vigentes_use_case: (
            ConsultarDesignacionesVigentesUseCase | None
        ) = None,
        consultar_historial_use_case: (ConsultarHistorialDocenteUseCase | None) = None,
    ) -> None:
        self._validar_use_case = (
            validar_use_case
            if validar_use_case is not None
            else ValidarHorariosDocenciaUseCase()
        )
        self._registrar_use_case = registrar_use_case
        self._cesar_use_case = cesar_use_case
        self._consultar_vigentes_use_case = consultar_vigentes_use_case
        self._consultar_historial_use_case = consultar_historial_use_case

    def validar_declaracion(
        self,
        input_dto: DeclaracionHorariaInputDTO,
    ) -> ResultadoCompatibilidadDTO:
        """Audita una declaración horaria ad-hoc y retorna el reporte de compatibilidad."""
        return self._validar_use_case.execute(input_dto)

    def registrar_designacion(
        self,
        input_dto: RegistrarDesignacionInputDTO,
    ) -> DesignacionDocenteDTO:
        """Persiste una nueva designación o suplencia con vigencia temporal."""
        if self._registrar_use_case is None:
            raise RuntimeError(
                "RegistrarDesignacionUseCase no inyectado en el controlador"
            )
        return self._registrar_use_case.execute(input_dto)

    def cesar_designacion(
        self,
        id_designacion: str,
        input_dto: CesarDesignacionInputDTO,
    ) -> DesignacionDocenteDTO | None:
        """Sella la fecha de fin y motivo de cese de una designación."""
        if self._cesar_use_case is None:
            raise RuntimeError("CesarDesignacionUseCase no inyectado en el controlador")
        return self._cesar_use_case.execute(id_designacion, input_dto)

    def consultar_vigentes_en_fecha(
        self,
        docente_cuit: str,
        fecha_str: str | None = None,
        margen_traslado_minutos: int = 20,
    ) -> ResultadoCompatibilidadDTO:
        """Recupera los cargos vigentes en una fecha y audita su compatibilidad."""
        if self._consultar_vigentes_use_case is None:
            raise RuntimeError(
                "ConsultarDesignacionesVigentesUseCase no inyectado en el controlador"
            )
        f_eval = date.fromisoformat(fecha_str.strip()) if fecha_str else None
        return self._consultar_vigentes_use_case.execute(
            docente_cuit=docente_cuit,
            fecha=f_eval,
            margen_traslado_minutos=margen_traslado_minutos,
        )

    def consultar_historial(
        self,
        docente_cuit: str,
    ) -> list[DesignacionDocenteDTO]:
        """Retorna la línea de tiempo completa del docente."""
        if self._consultar_historial_use_case is None:
            raise RuntimeError(
                "ConsultarHistorialDocenteUseCase no inyectado en el controlador"
            )
        return self._consultar_historial_use_case.execute(docente_cuit)
