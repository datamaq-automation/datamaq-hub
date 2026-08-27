"""Caso de uso para consultar y auditar la compatibilidad de designaciones vigentes en una fecha."""

from datetime import date

from src.application.dtos.horarios_docencia_dto import ResultadoCompatibilidadDTO
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.entities import DeclaracionHorariaDocente
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.services import ValidadorHorariosDocenciaService


class ConsultarDesignacionesVigentesUseCase:
    """Recupera los cargos vigentes en una fecha determinada y audita su compatibilidad."""

    def __init__(
        self,
        repository: DesignacionDocenteRepositoryPort,
        validador: ValidadorHorariosDocenciaService | None = None,
    ) -> None:
        self._repository = repository
        self._validador = (
            validador if validador is not None else ValidadorHorariosDocenciaService()
        )

    def execute(
        self,
        docente_cuit: str,
        fecha: date | None = None,
        margen_traslado_minutos: int = 20,
    ) -> ResultadoCompatibilidadDTO:
        """Audita las designaciones activas en la fecha solicitada."""
        fecha_eval = fecha if fecha is not None else date.today()
        vigentes = self._repository.obtener_vigentes_en_fecha(
            docente_cuit=docente_cuit.strip(),
            fecha=fecha_eval,
        )

        cargos = tuple(d.to_cargo_docente() for d in vigentes)
        declaracion = DeclaracionHorariaDocente(
            docente_nombre=f"Docente CUIT {docente_cuit}",
            cuit=docente_cuit,
            cargos=cargos,
        )

        resultado = self._validador.validar(
            declaracion=declaracion,
            margen_traslado_minutos=margen_traslado_minutos,
        )
        return HorariosDocenciaMapper.to_dto(resultado)
