"""Controlador agnóstico de frameworks web para horarios de docencia y persistencia temporal."""

from datetime import date

from src.application.dtos.horarios_docencia_dto import (
    ActualizarDesignacionInputDTO,
    CesarDesignacionInputDTO,
    DeclaracionHorariaInputDTO,
    DesignacionDocenteDTO,
    RegistrarDesignacionInputDTO,
    RegistrarDesignacionResponseDTO,
    ResultadoCompatibilidadDTO,
)
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.application.use_cases.actualizar_designacion import (
    ActualizarDesignacionUseCase,
)
from src.application.use_cases.cesar_designacion import CesarDesignacionUseCase
from src.application.use_cases.consultar_designaciones_vigentes import (
    ConsultarDesignacionesVigentesUseCase,
)
from src.application.use_cases.consultar_historial_docente import (
    ConsultarHistorialDocenteUseCase,
)
from src.application.use_cases.eliminar_designacion import EliminarDesignacionUseCase
from src.application.use_cases.listar_designaciones import (
    ListarDesignacionesUseCase,
)
from src.application.use_cases.registrar_designacion import (
    RegistrarDesignacionUseCase,
)
from src.application.use_cases.validar_horarios_docencia import (
    ValidarHorariosDocenciaUseCase,
)
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort


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
        listar_use_case: ListarDesignacionesUseCase | None = None,
        actualizar_use_case: ActualizarDesignacionUseCase | None = None,
        eliminar_use_case: EliminarDesignacionUseCase | None = None,
        repository: DesignacionDocenteRepositoryPort | None = None,
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
        self._listar_use_case = listar_use_case
        self._actualizar_use_case = actualizar_use_case
        self._eliminar_use_case = eliminar_use_case
        self._repository = repository

    def validar_declaracion(
        self,
        input_dto: DeclaracionHorariaInputDTO,
    ) -> ResultadoCompatibilidadDTO:
        """Audita una declaración horaria ad-hoc y retorna el reporte de compatibilidad."""
        return self._validar_use_case.execute(input_dto)

    def registrar_designacion(
        self,
        input_dto: RegistrarDesignacionInputDTO,
    ) -> RegistrarDesignacionResponseDTO:
        """Persiste una nueva designación o suplencia con vigencia temporal y auditoría de compatibilidad."""
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

    def listar_designaciones(
        self,
        cuit: str | None = None,
        vigentes_al_str: str | None = None,
        establecimiento: str | None = None,
        distrito: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DesignacionDocenteDTO]:
        """Lista designaciones con filtros y paginación."""
        if self._listar_use_case is None:
            raise RuntimeError(
                "ListarDesignacionesUseCase no inyectado en el controlador"
            )
        vigentes_al = (
            date.fromisoformat(vigentes_al_str.strip()) if vigentes_al_str else None
        )
        return self._listar_use_case.execute(
            cuit=cuit,
            vigentes_al=vigentes_al,
            establecimiento=establecimiento,
            distrito=distrito,
            limit=limit,
            offset=offset,
        )

    def obtener_designacion_por_id(
        self, id_designacion: str
    ) -> DesignacionDocenteDTO | None:
        """Obtiene una designación por su ID único."""
        if self._repository is None:
            raise RuntimeError("Repository no inyectado en HorariosDocenciaController")
        desig = self._repository.obtener_por_id(id_designacion.strip())
        return HorariosDocenciaMapper.designacion_to_dto(desig) if desig else None

    def actualizar_designacion(
        self, id_designacion: str, input_dto: ActualizarDesignacionInputDTO
    ) -> DesignacionDocenteDTO | None:
        """Actualiza una designación existente."""
        if self._actualizar_use_case is None:
            raise RuntimeError(
                "ActualizarDesignacionUseCase no inyectado en el controlador"
            )
        return self._actualizar_use_case.execute(id_designacion, input_dto)

    def eliminar_designacion(self, id_designacion: str) -> bool:
        """Elimina físicamente una designación existente."""
        if self._eliminar_use_case is None:
            raise RuntimeError(
                "EliminarDesignacionUseCase no inyectado en el controlador"
            )
        return self._eliminar_use_case.execute(id_designacion)
