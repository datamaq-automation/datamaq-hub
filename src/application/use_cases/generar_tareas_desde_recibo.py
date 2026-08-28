"""Caso de uso para auto-generar tareas a partir de la conciliación de un recibo."""

from src.application.dtos.tarea_dtos import GenerarTareasReciboResponseDTO
from src.application.mappers.tarea_mapper import TareaMapper
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.recibos.exceptions import ReciboNotFoundError
from src.domain.recibos.ports import ReciboRepositoryPort
from src.domain.recibos.services import ConciliadorReciboDocenteService
from src.domain.tareas.ports import FiltrosTarea, TareaRepositoryPort
from src.domain.tareas.services import GeneradorTareasReciboService


class GenerarTareasDesdeReciboUseCase:
    """Detecta faltantes o discrepancias en la conciliación del recibo y crea tareas pendientes."""

    def __init__(
        self,
        recibo_repository: ReciboRepositoryPort,
        designacion_repository: DesignacionDocenteRepositoryPort,
        tarea_repository: TareaRepositoryPort,
        conciliador: ConciliadorReciboDocenteService | None = None,
    ) -> None:
        self._recibo_repository = recibo_repository
        self._designacion_repository = designacion_repository
        self._tarea_repository = tarea_repository
        self._conciliador = (
            conciliador
            if conciliador is not None
            else ConciliadorReciboDocenteService()
        )

    def execute(self, id_recibo: str) -> GenerarTareasReciboResponseDTO:
        recibo = self._recibo_repository.obtener_por_id(id_recibo)
        if not recibo:
            raise ReciboNotFoundError(
                f"Recibo de sueldo con ID '{id_recibo}' no encontrado."
            )

        cuit_normalizado = recibo.agente.cuil.replace("-", "").strip()
        designaciones = self._designacion_repository.obtener_historial(cuit_normalizado)

        resultado_conciliacion = self._conciliador.conciliar(
            recibo=recibo,
            designaciones=list(designaciones),
        )

        tareas_generadas_domain = (
            GeneradorTareasReciboService.generar_tareas_desde_conciliacion(
                resultado_conciliacion
            )
        )

        # Evitar duplicar tareas para el mismo recibo y título
        tareas_existentes = self._tarea_repository.listar(
            FiltrosTarea(id_referencia=id_recibo)
        )
        titulos_existentes = {t.titulo for t in tareas_existentes}

        guardadas = []
        for tg in tareas_generadas_domain:
            if tg.titulo not in titulos_existentes:
                t_guardada = self._tarea_repository.guardar(tg)
                guardadas.append(TareaMapper.to_dto(t_guardada))
                titulos_existentes.add(tg.titulo)

        return GenerarTareasReciboResponseDTO(
            id_recibo=id_recibo,
            total_generadas=len(guardadas),
            tareas=guardadas,
        )
