"""Caso de uso para registrar una nueva designación o suplencia docente con vigencia temporal."""

from src.application.dtos.horarios_docencia_dto import (
    RegistrarDesignacionInputDTO,
    RegistrarDesignacionResponseDTO,
)
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.entities import DeclaracionHorariaDocente
from src.domain.horarios_docencia.exceptions import (
    IncompatibilidadHorariaCriticaException,
)
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.services import ValidadorHorariosDocenciaService


class RegistrarDesignacionUseCase:
    """Orquesta el registro inmutable de una designación docente con auditoría inmediata de compatibilidad."""

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
        self, input_dto: RegistrarDesignacionInputDTO
    ) -> RegistrarDesignacionResponseDTO:
        """Persiste la designación y retorna su representación DTO junto con el veredicto de compatibilidad."""
        designacion_domain = HorariosDocenciaMapper.to_designacion_domain(input_dto)

        # 1. Recuperar cargos vigentes en la fecha de inicio para auditar solapamientos
        vigentes = self._repository.obtener_vigentes_en_fecha(
            docente_cuit=designacion_domain.docente_cuit,
            fecha=designacion_domain.vigencia.fecha_desde,
        )

        cargos = [d.to_cargo_docente() for d in vigentes]
        cargos.append(designacion_domain.to_cargo_docente())

        declaracion = DeclaracionHorariaDocente(
            docente_nombre=f"Docente CUIT {designacion_domain.docente_cuit}",
            cuit=designacion_domain.docente_cuit,
            cargos=tuple(cargos),
        )

        resultado = self._validador.validar(declaracion=declaracion)
        resultado_dto = HorariosDocenciaMapper.to_dto(resultado)

        # 2. Bloquear persistencia si hay incompatibilidad crítica y no se envió forzar=True
        if not resultado.es_compatible and not input_dto.forzar:
            conflictos_criticos = [
                c.descripcion
                for c in resultado.conflictos
                if c.severidad.value == "CRITICO"
            ]
            detalle = (
                "; ".join(conflictos_criticos)
                if conflictos_criticos
                else "Superposición horaria crítica detectada"
            )
            raise IncompatibilidadHorariaCriticaException(
                mensaje=(
                    f"No se puede registrar la designación por superposición horaria crítica: {detalle}. "
                    "Para forzar el guardado de todas formas envíe 'forzar: true'."
                ),
                conflictos=tuple(resultado.conflictos),
            )

        # 3. Guardar designación
        guardada = self._repository.guardar(designacion_domain)
        designacion_dto = HorariosDocenciaMapper.designacion_to_dto(guardada)

        return RegistrarDesignacionResponseDTO(
            designacion=designacion_dto,
            es_compatible=resultado_dto.es_compatible,
            advertencias=resultado_dto.conflictos,
        )
