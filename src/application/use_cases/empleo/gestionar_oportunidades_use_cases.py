"""Use cases for managing job opportunities and application interactions."""

from src.application.dtos.empleo_dtos import (
    ActualizarEstadoOportunidadDTO,
    InteraccionDTO,
    OportunidadDTO,
    RegistrarInteraccionDTO,
    RegistrarOportunidadDTO,
)
from src.application.mappers.empleo_mapper import EmpleoMapper
from src.domain.empleo.ports import OportunidadesRepositoryPort
from src.domain.empleo.value_objects import EstadoOportunidad


class RegistrarOportunidadUseCase:
    """Caso de uso para registrar una nueva oportunidad o postulación."""

    def __init__(self, repository: OportunidadesRepositoryPort) -> None:
        self._repository = repository

    def execute(self, dto: RegistrarOportunidadDTO) -> OportunidadDTO:
        entidad = EmpleoMapper.oportunidad_dto_a_entidad(dto)
        guardada = self._repository.guardar(entidad)
        return EmpleoMapper.oportunidad_entidad_a_dto(guardada)


class ListarOportunidadesUseCase:
    """Caso de uso para listar oportunidades laborales con filtros opcionales."""

    def __init__(self, repository: OportunidadesRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        estado: str | EstadoOportunidad | None = None,
        empresa: str | None = None,
    ) -> list[OportunidadDTO]:
        estado_vo: EstadoOportunidad | None = None
        if isinstance(estado, EstadoOportunidad):
            estado_vo = estado
        elif isinstance(estado, str) and estado.strip():
            try:
                estado_vo = EstadoOportunidad(estado.strip().upper())
            except ValueError:
                estado_vo = None

        oportunidades = self._repository.listar(estado=estado_vo, empresa=empresa)
        return [EmpleoMapper.oportunidad_entidad_a_dto(op) for op in oportunidades]


class ActualizarEstadoOportunidadUseCase:
    """Caso de uso para actualizar el estado del embudo y notas de una oportunidad."""

    def __init__(self, repository: OportunidadesRepositoryPort) -> None:
        self._repository = repository

    def execute(self, dto: ActualizarEstadoOportunidadDTO) -> OportunidadDTO:
        try:
            estado_vo = EstadoOportunidad(dto.nuevo_estado.upper())
        except (ValueError, AttributeError):
            estado_vo = EstadoOportunidad.DETECTADA

        actualizada = self._repository.actualizar_estado(
            id_oportunidad=dto.id_oportunidad,
            nuevo_estado=estado_vo,
            notas=dto.notas,
        )
        return EmpleoMapper.oportunidad_entidad_a_dto(actualizada)


class RegistrarInteraccionUseCase:
    """Caso de uso para registrar una interacción o seguimiento de postulación."""

    def __init__(self, repository: OportunidadesRepositoryPort) -> None:
        self._repository = repository

    def execute(self, dto: RegistrarInteraccionDTO) -> InteraccionDTO:
        entidad = EmpleoMapper.interaccion_dto_a_entidad(dto)
        guardada = self._repository.registrar_interaccion(entidad)
        return EmpleoMapper.interaccion_entidad_a_dto(guardada)


class ListarInteraccionesUseCase:
    """Caso de uso para listar las interacciones de una oportunidad."""

    def __init__(self, repository: OportunidadesRepositoryPort) -> None:
        self._repository = repository

    def execute(self, oportunidad_id: int) -> list[InteraccionDTO]:
        interacciones = self._repository.listar_interacciones(
            oportunidad_id=oportunidad_id
        )
        return [EmpleoMapper.interaccion_entidad_a_dto(i) for i in interacciones]
