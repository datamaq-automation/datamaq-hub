from typing import Any

from src.adapters.presenters.receipt_presenter import ReceiptPresenter
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.conciliacion_dto import (
    ConciliacionResponseDTO,
    ConfirmarPropuestasDTO,
    DesignacionNoLiquidadaDTO,
    PropuestaDesignacionDTO,
)
from src.application.dtos.horarios_docencia_dto import DesignacionDocenteDTO
from src.application.dtos.receipt_dto import (
    DesgloseFinancieroDTO,
    ReceiptResponseDTO,
    ReceiptSummaryDTO,
)
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.application.use_cases.conciliar_recibo import ConciliarReciboUseCase
from src.application.use_cases.crear_designaciones_desde_recibo import (
    CrearDesignacionesDesdeReciboUseCase,
)
from src.application.use_cases.eliminar_recibo import EliminarReciboUseCase
from src.application.use_cases.gestionar_propuestas_huerfanas import (
    GestionarPropuestasHuerfanasUseCase,
)
from src.application.use_cases.listar_recibos import ListarRecibosUseCase
from src.application.use_cases.obtener_recibo import ObtenerReciboUseCase
from src.application.use_cases.parse_receipt import ParseReceiptUseCase
from src.domain.recibos.ports import SeguimientoNoLiquidadosRepositoryPort


class ReceiptController:
    """Handles receipt parsing, persistence and reconciliation operations independently of web transport."""

    def __init__(
        self,
        parse_use_case: ParseReceiptUseCase,
        obtener_use_case: ObtenerReciboUseCase | None = None,
        listar_use_case: ListarRecibosUseCase | None = None,
        eliminar_use_case: EliminarReciboUseCase | None = None,
        conciliar_use_case: ConciliarReciboUseCase | None = None,
        crear_desde_recibo_use_case: CrearDesignacionesDesdeReciboUseCase | None = None,
        gestionar_propuestas_use_case: GestionarPropuestasHuerfanasUseCase
        | None = None,
        seguimiento_repository: SeguimientoNoLiquidadosRepositoryPort | None = None,
    ) -> None:
        self._parse_use_case = parse_use_case
        self._obtener_use_case = obtener_use_case
        self._listar_use_case = listar_use_case
        self._eliminar_use_case = eliminar_use_case
        self._conciliar_use_case = conciliar_use_case
        self._crear_desde_recibo_use_case = crear_desde_recibo_use_case
        self._gestionar_propuestas_use_case = gestionar_propuestas_use_case
        self._seguimiento_repository = seguimiento_repository

    def parse_bytes(
        self,
        content: bytes,
        filename: str = "receipt.pdf",
        persistir: bool = True,
        solo_resumen: bool = False,
    ) -> APIResponseDTO[ReceiptResponseDTO] | APIResponseDTO[ReceiptSummaryDTO]:
        """Execute receipt parsing on byte stream and present envelope."""
        receipt_dto = self._parse_use_case.execute_bytes(
            content, filename=filename, persistir=persistir
        )
        if solo_resumen:
            return APIResponseDTO[ReceiptSummaryDTO](
                success=True, data=ReceiptMapper.to_summary(receipt_dto)
            )
        return ReceiptPresenter.present(receipt_dto)

    def obtener_por_id(self, id_recibo: str) -> APIResponseDTO[ReceiptResponseDTO]:
        """Recupera un recibo persistido por su identificador."""
        if not self._obtener_use_case:
            raise RuntimeError("ObtenerReciboUseCase no configurado.")
        dto = self._obtener_use_case.execute(id_recibo)
        return ReceiptPresenter.present(dto)

    def listar(
        self,
        cuit: str | None = None,
        mes_pago: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> APIResponseDTO[list[ReceiptResponseDTO]]:
        """Lista recibos de sueldo persistidos con paginación y filtros."""
        if not self._listar_use_case:
            raise RuntimeError("ListarRecibosUseCase no configurado.")
        dtos = self._listar_use_case.execute(
            cuit=cuit, mes_pago=mes_pago, limit=limit, offset=offset
        )
        return APIResponseDTO(success=True, data=dtos)

    def eliminar(self, id_recibo: str) -> APIResponseDTO[dict[str, Any]]:
        """Elimina un recibo persistido."""
        if not self._eliminar_use_case:
            raise RuntimeError("EliminarReciboUseCase no configurado.")
        self._eliminar_use_case.execute(id_recibo)
        return APIResponseDTO(
            success=True, data={"eliminado": True, "id_recibo": id_recibo}
        )

    def conciliar(self, id_recibo: str) -> APIResponseDTO[ConciliacionResponseDTO]:
        """Ejecuta la conciliación automática entre el recibo y las designaciones del docente."""
        if not self._conciliar_use_case:
            raise RuntimeError("ConciliarReciboUseCase no configurado.")
        resultado_dto = self._conciliar_use_case.execute(id_recibo)
        return APIResponseDTO(success=True, data=resultado_dto)

    def crear_designaciones_huerfanas(
        self,
        id_recibo: str,
        secuencias: list[str] | None = None,
    ) -> APIResponseDTO[list[DesignacionDocenteDTO]]:
        """Auto-genera designaciones históricas a partir de las líneas no registradas del recibo."""
        if not self._crear_desde_recibo_use_case:
            raise RuntimeError("CrearDesignacionesDesdeReciboUseCase no configurado.")
        creadas = self._crear_desde_recibo_use_case.execute(
            id_recibo=id_recibo, secuencias=secuencias
        )
        return APIResponseDTO(success=True, data=creadas)

    def desglosar(self, id_recibo: str) -> APIResponseDTO[DesgloseFinancieroDTO]:
        """Obtiene el desglose financiero (nominal, retroactivo, SAC, otros) de un recibo."""
        if not self._obtener_use_case:
            raise RuntimeError("ObtenerReciboUseCase no configurado.")
        dto = self._obtener_use_case.execute(id_recibo)
        return APIResponseDTO[DesgloseFinancieroDTO](
            success=True,
            data=dto.desglose
            or DesgloseFinancieroDTO(
                mes_pago=dto.agente.mes_pago,
                total_liquido=dto.totales.total_liquido,
                importe_periodo_nominal=0.0,
                importe_retroactivos=0.0,
                importe_sac=0.0,
                importe_otros=0.0,
            ),
        )

    def exportar_conciliacion_csv(self, id_recibo: str) -> str:
        """Genera el contenido CSV (separador ';', UTF-8) del resultado de conciliación."""
        if not self._conciliar_use_case:
            raise RuntimeError("ConciliarReciboUseCase no configurado.")
        conciliacion = self._conciliar_use_case.execute(id_recibo)
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(
            [
                "tipo_linea",
                "secuencia",
                "escuela_codigo",
                "periodo_liquidado",
                "revista_recibo",
                "revista_designacion",
                "modulos_recibo",
                "modulos_designacion",
                "liquido_pesos",
                "estado",
                "es_retroactivo",
                "id_designacion",
                "observacion",
            ]
        )
        for c in conciliacion.lineas_conciliadas:
            writer.writerow(
                [
                    "CONCILIADA",
                    c.secuencia,
                    c.escuela_codigo,
                    c.periodo_liquidado,
                    c.revista_recibo,
                    c.revista_designacion or "",
                    c.modulos_recibo,
                    c.modulos_designacion if c.modulos_designacion is not None else "",
                    f"{c.liquido_pesos:.2f}",
                    c.estado,
                    "SI" if c.es_retroactivo else "NO",
                    c.id_designacion or "",
                    c.observacion or "",
                ]
            )
        for h in conciliacion.lineas_huerfanas_recibo:
            writer.writerow(
                [
                    "HUERFANA",
                    h.secuencia,
                    h.escuela_codigo,
                    h.periodo_liquidado,
                    h.revista_recibo,
                    "",
                    h.modulos_recibo,
                    "",
                    f"{h.liquido_pesos:.2f}",
                    h.estado,
                    "SI" if h.es_retroactivo else "NO",
                    "",
                    h.observacion or "Línea cobrada sin designación registrada",
                ]
            )
        for nd in conciliacion.designaciones_no_cobradas:
            writer.writerow(
                [
                    "NO_COBRADA",
                    nd.secuencia,
                    nd.escuela_codigo,
                    nd.periodo_liquidado,
                    "",
                    nd.revista_designacion or "",
                    "",
                    nd.modulos_designacion
                    if nd.modulos_designacion is not None
                    else "",
                    f"{nd.liquido_pesos:.2f}",
                    nd.estado,
                    "NO",
                    nd.id_designacion or "",
                    nd.observacion
                    or "Designación activa no encontrada en liquidaciones",
                ]
            )
        return output.getvalue()

    def obtener_propuestas_huerfanas(
        self, id_recibo: str
    ) -> APIResponseDTO[list[PropuestaDesignacionDTO]]:
        """Obtiene borradores estructurados precargados para las líneas huérfanas del recibo."""
        if not self._gestionar_propuestas_use_case:
            raise RuntimeError("GestionarPropuestasHuerfanasUseCase no configurado.")
        propuestas = self._gestionar_propuestas_use_case.obtener_propuestas(id_recibo)
        return APIResponseDTO[list[PropuestaDesignacionDTO]](
            success=True, data=propuestas
        )

    def confirmar_propuestas_huerfanas(
        self, id_recibo: str, solicitud: ConfirmarPropuestasDTO
    ) -> APIResponseDTO[list[DesignacionDocenteDTO]]:
        """Persiste las designaciones huérfanas explícitamente confirmadas por el usuario."""
        if not self._gestionar_propuestas_use_case:
            raise RuntimeError("GestionarPropuestasHuerfanasUseCase no configurado.")
        creadas = self._gestionar_propuestas_use_case.confirmar_propuestas(
            id_recibo=id_recibo, solicitud=solicitud
        )
        if self._conciliar_use_case:
            self._conciliar_use_case.execute(id_recibo)
        return APIResponseDTO[list[DesignacionDocenteDTO]](success=True, data=creadas)

    def obtener_no_liquidados_recibo(
        self, id_recibo: str
    ) -> APIResponseDTO[list[DesignacionNoLiquidadaDTO]]:
        """Obtiene las designaciones vigentes no cobradas en un recibo específico."""
        if not self._seguimiento_repository:
            raise RuntimeError("SeguimientoNoLiquidadosRepositoryPort no configurado.")
        domain_items = self._seguimiento_repository.obtener_por_recibo(id_recibo)
        dtos = [
            DesignacionNoLiquidadaDTO(
                id_seguimiento=item.id_seguimiento,
                id_recibo=item.id_recibo,
                id_designacion=item.id_designacion,
                docente_cuit=item.docente_cuit,
                mes_pago=item.mes_pago,
                secuencia=item.secuencia,
                escuela_codigo=item.escuela_codigo,
                modulos=item.modulos,
                situacion_revista=item.situacion_revista,
                periodos_consecutivos=item.periodos_consecutivos,
                alerta_2_periodos=item.alerta_2_periodos,
                estado=item.estado,
                id_recibo_resolucion=item.id_recibo_resolucion,
                creado_en=item.creado_en,
            )
            for item in domain_items
        ]
        return APIResponseDTO[list[DesignacionNoLiquidadaDTO]](success=True, data=dtos)

    def listar_no_liquidados(
        self,
        cuit: str | None = None,
        solo_pendientes: bool = False,
        solo_alertas: bool = False,
    ) -> APIResponseDTO[list[DesignacionNoLiquidadaDTO]]:
        """Obtiene el historial y seguimiento diferido de designaciones no liquidadas."""
        if not self._seguimiento_repository:
            raise RuntimeError("SeguimientoNoLiquidadosRepositoryPort no configurado.")
        domain_items = self._seguimiento_repository.listar(
            docente_cuit=cuit,
            solo_pendientes=solo_pendientes,
            solo_alertas=solo_alertas,
        )
        dtos = [
            DesignacionNoLiquidadaDTO(
                id_seguimiento=item.id_seguimiento,
                id_recibo=item.id_recibo,
                id_designacion=item.id_designacion,
                docente_cuit=item.docente_cuit,
                mes_pago=item.mes_pago,
                secuencia=item.secuencia,
                escuela_codigo=item.escuela_codigo,
                modulos=item.modulos,
                situacion_revista=item.situacion_revista,
                periodos_consecutivos=item.periodos_consecutivos,
                alerta_2_periodos=item.alerta_2_periodos,
                estado=item.estado,
                id_recibo_resolucion=item.id_recibo_resolucion,
                creado_en=item.creado_en,
            )
            for item in domain_items
        ]
        return APIResponseDTO[list[DesignacionNoLiquidadaDTO]](success=True, data=dtos)
