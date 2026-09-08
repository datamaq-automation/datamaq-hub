from src.application.dtos.conciliacion_dto import ConciliacionResponseDTO
from src.application.mappers.conciliacion_mapper import ConciliacionMapper
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.recibos.entities import DesignacionNoLiquidada
from src.domain.recibos.exceptions import ReciboNotFoundError
from src.domain.recibos.ports import (
    ReciboRepositoryPort,
    SeguimientoNoLiquidadosRepositoryPort,
)
from src.domain.recibos.services import ConciliadorReciboDocenteService


class ConciliarReciboUseCase:
    """Orquesta la auditoría y conciliación mensual: lo liquidado en recibo vs lo designado en escuelas."""

    def __init__(
        self,
        recibo_repository: ReciboRepositoryPort,
        designacion_repository: DesignacionDocenteRepositoryPort,
        conciliador: ConciliadorReciboDocenteService | None = None,
        seguimiento_repository: SeguimientoNoLiquidadosRepositoryPort | None = None,
    ) -> None:
        self._recibo_repository = recibo_repository
        self._designacion_repository = designacion_repository
        self._conciliador = (
            conciliador
            if conciliador is not None
            else ConciliadorReciboDocenteService()
        )
        self._seguimiento_repository = seguimiento_repository

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

        if self._seguimiento_repository:
            # 1. Marcar como resueltas las designaciones que se liquidaron en este recibo
            conciliadas_ids = [
                lc.id_designacion
                for lc in resultado.lineas_conciliadas
                if lc.id_designacion
            ]
            if conciliadas_ids:
                self._seguimiento_repository.resolver_designaciones(
                    docente_cuit=cuit_normalizado,
                    ids_designacion=conciliadas_ids,
                    id_recibo_resolucion=id_recibo,
                )

            # 2. Procesar designaciones no cobradas en este recibo
            pendientes_anteriores = {
                item.id_designacion: item
                for item in self._seguimiento_repository.obtener_ultimas_pendientes(
                    cuit_normalizado
                )
                if item.id_recibo != id_recibo
            }
            no_liquidadas_batch: list[DesignacionNoLiquidada] = []
            for nd in resultado.designaciones_no_cobradas:
                if not nd.id_designacion:
                    continue
                previo = pendientes_anteriores.get(nd.id_designacion)
                consecutivos = (previo.periodos_consecutivos + 1) if previo else 1
                alerta = consecutivos >= 2
                item = DesignacionNoLiquidada(
                    id_recibo=id_recibo,
                    id_designacion=nd.id_designacion,
                    docente_cuit=cuit_normalizado,
                    mes_pago=recibo.agente.mes_pago,
                    secuencia=nd.secuencia,
                    escuela_codigo=nd.escuela_codigo,
                    modulos=nd.modulos_designacion or 0.0,
                    situacion_revista=nd.revista_designacion or "",
                    periodos_consecutivos=consecutivos,
                    alerta_2_periodos=alerta,
                    estado="PENDIENTE",
                )
                no_liquidadas_batch.append(item)

            if no_liquidadas_batch:
                self._seguimiento_repository.guardar_batch(no_liquidadas_batch)

        return ConciliacionMapper.to_dto(resultado)
