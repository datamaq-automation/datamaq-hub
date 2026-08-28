"""Caso de uso para conciliar un recibo de sueldo frente a las designaciones docentes históricas."""

from src.application.dtos.conciliacion_dto import ConciliacionResponseDTO
from src.application.mappers.conciliacion_mapper import ConciliacionMapper
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.recibos.exceptions import ReciboNotFoundError
from src.domain.recibos.ports import ReciboRepositoryPort
from src.domain.recibos.services import ConciliadorReciboDocenteService


class ConciliarReciboUseCase:
    """Orquesta la auditoría y conciliación mensual: lo liquidado en recibo vs lo designado en escuelas."""

    def __init__(
        self,
        recibo_repository: ReciboRepositoryPort,
        designacion_repository: DesignacionDocenteRepositoryPort,
        conciliador: ConciliadorReciboDocenteService | None = None,
    ) -> None:
        self._recibo_repository = recibo_repository
        self._designacion_repository = designacion_repository
        self._conciliador = (
            conciliador
            if conciliador is not None
            else ConciliadorReciboDocenteService()
        )

    def execute(self, id_recibo: str) -> ConciliacionResponseDTO:
        recibo = self._recibo_repository.obtener_por_id(id_recibo)
        if not recibo:
            raise ReciboNotFoundError(
                f"Recibo de sueldo con ID '{id_recibo}' no encontrado."
            )

        cuit_normalizado = recibo.agente.cuil.replace("-", "").strip()

        # Recuperar historial completo de designaciones del docente (activas y cesadas)
        designaciones = self._designacion_repository.obtener_historial(cuit_normalizado)

        resultado = self._conciliador.conciliar(
            recibo=recibo,
            designaciones=list(designaciones),
        )

        return ConciliacionMapper.to_dto(resultado)
