"""Mapper para transformar entidades de conciliación en DTOs de respuesta."""

from src.application.dtos.conciliacion_dto import (
    CargoConciliadoDTO,
    ConciliacionResponseDTO,
    LineaConciliadaDTO,
)
from src.domain.recibos.entities import (
    CargoConciliado,
    LineaConciliada,
    ResultadoConciliacion,
)


class ConciliacionMapper:
    """Transforma ResultadoConciliacion domain entity a ConciliacionResponseDTO."""

    @staticmethod
    def to_dto(entity: ResultadoConciliacion) -> ConciliacionResponseDTO:
        return ConciliacionResponseDTO(
            id_recibo=entity.id_recibo,
            mes_pago=entity.mes_pago,
            docente_cuit=entity.docente_cuit,
            total_lineas_recibo=entity.total_lineas_recibo,
            total_designaciones_evaluadas=entity.total_designaciones_evaluadas,
            lineas_conciliadas=[
                ConciliacionMapper._linea_to_dto(l) for l in entity.lineas_conciliadas
            ],
            lineas_huerfanas_recibo=[
                ConciliacionMapper._linea_to_dto(l)
                for l in entity.lineas_huerfanas_recibo
            ],
            designaciones_no_cobradas=[
                ConciliacionMapper._linea_to_dto(l)
                for l in entity.designaciones_no_cobradas
            ],
            cargos_conciliados=[
                ConciliacionMapper._cargo_to_dto(c) for c in entity.cargos_conciliados
            ],
            cargos_huerfanos_recibo=[
                ConciliacionMapper._cargo_to_dto(c)
                for c in entity.cargos_huerfanos_recibo
            ],
            total_liquidado_recibo=entity.total_liquidado_recibo,
            total_liquidado_conciliado=entity.total_liquidado_conciliado,
            total_liquidado_huerfano=entity.total_liquidado_huerfano,
            es_conciliacion_completa=entity.es_conciliacion_completa,
            resumen_financiero={
                "porcentaje_conciliado": (
                    round(
                        (
                            entity.total_liquidado_conciliado
                            / entity.total_liquidado_recibo
                        )
                        * 100,
                        1,
                    )
                    if entity.total_liquidado_recibo > 0
                    else 100.0
                ),
                "monto_sin_respaldo": entity.total_liquidado_huerfano,
                "cantidad_lineas_huerfanas": len(entity.lineas_huerfanas_recibo),
                "cantidad_cargos_no_cobrados": len(entity.designaciones_no_cobradas),
            },
        )

    @staticmethod
    def _linea_to_dto(linea: LineaConciliada) -> LineaConciliadaDTO:
        return LineaConciliadaDTO(
            id_designacion=linea.id_designacion,
            secuencia=linea.secuencia,
            escuela_codigo=linea.escuela_codigo,
            periodo_liquidado=linea.periodo_liquidado,
            revista_recibo=linea.revista_recibo,
            revista_designacion=linea.revista_designacion,
            modulos_recibo=linea.modulos_recibo,
            modulos_designacion=linea.modulos_designacion,
            liquido_pesos=linea.liquido_pesos,
            estado=linea.estado,
            es_retroactivo=linea.es_retroactivo,
            observacion=linea.observacion,
        )

    @staticmethod
    def _cargo_to_dto(cargo: CargoConciliado) -> CargoConciliadoDTO:
        return CargoConciliadoDTO(
            secuencia=cargo.secuencia,
            escuela_codigo=cargo.escuela_codigo,
            id_designacion=cargo.id_designacion,
            revista_recibo=cargo.revista_recibo,
            revista_designacion=cargo.revista_designacion,
            modulos_recibo=cargo.modulos_recibo,
            modulos_designacion=cargo.modulos_designacion,
            importe_total=cargo.importe_total,
            cantidad_lineas=cargo.cantidad_lineas,
            estado=cargo.estado,
            lineas_explicadas=[
                ConciliacionMapper._linea_to_dto(l) for l in cargo.lineas_explicadas
            ],
            observacion=cargo.observacion,
        )
