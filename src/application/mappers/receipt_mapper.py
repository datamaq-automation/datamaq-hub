"""Mapper to transform Domain Entities into Application DTOs."""

from src.application.dtos.receipt_dto import (
    AgenteDTO,
    CargoDTO,
    ConceptoItemDTO,
    EmpleadorDTO,
    EstablecimientoDTO,
    LiquidacionSecuenciaDTO,
    ReceiptResponseDTO,
    ResumenLiquidoItemDTO,
    TotalesConsolidadosDTO,
)
from src.domain.recibos.entities import ReciboSueldo


class ReceiptMapper:
    """Transforms ReciboSueldo domain entity aggregate into ReceiptResponseDTO."""

    @staticmethod
    def to_dto(entity: ReciboSueldo) -> ReceiptResponseDTO:
        return ReceiptResponseDTO(
            tipo_recibo=entity.tipo_recibo,
            empleador=EmpleadorDTO(
                organismo_o_empresa=entity.empleador.organismo_o_empresa,
                dependencia=entity.empleador.dependencia,
                cuit=entity.empleador.cuit,
            ),
            agente=AgenteDTO(
                nombre_completo=entity.agente.nombre_completo,
                tipo_documento=entity.agente.tipo_documento,
                numero_documento=entity.agente.numero_documento,
                sexo=entity.agente.sexo,
                cuil=entity.agente.cuil,
                mes_pago=entity.agente.mes_pago,
            ),
            resumen_liquidos=[
                ResumenLiquidoItemDTO(
                    establecimiento_codigo=item.establecimiento_codigo,
                    secuencia=item.secuencia,
                    periodo_liquidado=item.periodo_liquidado,
                    fecha_pago=item.fecha_pago,
                    orden_pago_codigo=item.orden_pago_codigo,
                    orden_pago_descripcion=item.orden_pago_descripcion,
                    liquido_pesos=item.liquido_pesos,
                )
                for item in entity.resumen_liquidos
            ],
            liquidaciones=[
                LiquidacionSecuenciaDTO(
                    establecimiento=EstablecimientoDTO(
                        codigo=liq.establecimiento.codigo,
                        distrito=liq.establecimiento.distrito,
                        categoria=liq.establecimiento.categoria,
                        desfavorabilidad=liq.establecimiento.desfavorabilidad,
                        secciones=liq.establecimiento.secciones,
                        es_carcel=liq.establecimiento.es_carcel,
                        doble_escolaridad=liq.establecimiento.doble_escolaridad,
                        turnos=liq.establecimiento.turnos,
                        nombre=liq.establecimiento.nombre,
                    ),
                    cargo=CargoDTO(
                        secuencia=liq.cargo.secuencia,
                        situacion_revista=liq.cargo.situacion_revista,
                        cargo_real=liq.cargo.cargo_real,
                        carga_horaria=liq.cargo.carga_horaria,
                        antiguedad_anios=liq.cargo.antiguedad_anios,
                        dias_trabajados=liq.cargo.dias_trabajados,
                        inasistencias=liq.cargo.inasistencias,
                        periodo_liquidado=liq.cargo.periodo_liquidado,
                        orden_pago=liq.cargo.orden_pago,
                    ),
                    conceptos=[
                        ConceptoItemDTO(
                            codigo=c.codigo,
                            descripcion=c.descripcion,
                            haberes=c.haberes,
                            descuentos=c.descuentos,
                            tipo=c.tipo,
                        )
                        for c in liq.conceptos
                    ],
                    subtotal_haberes=liq.subtotal_haberes,
                    subtotal_descuentos=liq.subtotal_descuentos,
                    liquido_calculado=liq.liquido_calculado,
                )
                for liq in entity.liquidaciones
            ],
            totales=TotalesConsolidadosDTO(
                total_haberes_remunerativos=entity.totales.total_haberes_remunerativos,
                total_haberes_no_remunerativos=entity.totales.total_haberes_no_remunerativos,
                total_haberes=entity.totales.total_haberes,
                total_descuentos=entity.totales.total_descuentos,
                total_liquido=entity.totales.total_liquido,
            ),
            metadata=dict(entity.metadata),
        )
