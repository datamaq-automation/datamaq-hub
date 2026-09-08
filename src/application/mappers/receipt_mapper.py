"""Mapper to transform Domain Entities into Application DTOs."""

import re

from src.application.dtos.receipt_dto import (
    AgenteDTO,
    CargoDTO,
    ConceptoItemDTO,
    DesgloseFinancieroDTO,
    EmpleadorDTO,
    EstablecimientoDTO,
    LiquidacionSecuenciaDTO,
    ReceiptResponseDTO,
    ReceiptSummaryDTO,
    ResumenLiquidoItemDTO,
    TotalesConsolidadosDTO,
)
from src.domain.recibos.entities import ReciboSueldo


class ReceiptMapper:
    """Transforms ReciboSueldo domain entity aggregate into ReceiptResponseDTO."""

    @staticmethod
    def to_dto(entity: ReciboSueldo) -> ReceiptResponseDTO:
        return ReceiptResponseDTO(
            id_recibo=entity.id_recibo if entity.id_recibo else None,
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
                    distrito=item.distrito,
                    tipo_nivel=item.tipo_nivel,
                    escuela=item.escuela,
                    revista=item.revista,
                    orden_pago=item.orden_pago,
                    importe=item.importe
                    if item.importe is not None
                    else item.liquido_pesos,
                    concepto_normalizado=item.concepto_normalizado,
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
                total_declarado=entity.totales.total_declarado,
                diferencia_cierre=entity.totales.diferencia_cierre,
                estado_cierre=entity.totales.estado_cierre,
            ),
            pdf_hash=entity.pdf_hash,
            es_duplicado=entity.es_duplicado,
            estado_cierre=entity.totales.estado_cierre,
            total_declarado=entity.totales.total_declarado,
            diferencia_cierre=entity.totales.diferencia_cierre,
            desglose=ReceiptMapper._calcular_desglose(entity),
            metadata=dict(entity.metadata),
        )

    @classmethod
    def _calcular_desglose(cls, entity: ReciboSueldo) -> DesgloseFinancieroDTO:
        def _to_ym(raw: str | None) -> str:
            val = (raw or "").strip()
            if not val:
                return ""
            if "/" in val:
                parts = [p.strip() for p in val.split("/") if p.strip()]
                if len(parts) == 2 and len(parts[0]) <= 2 and len(parts[1]) == 4:
                    return f"{parts[1]}{parts[0].zfill(2)}"
            digits = re.sub(r"\D", "", val)
            if len(digits) == 6:
                return digits
            return digits

        mes_pago_norm = _to_ym(entity.agente.mes_pago)
        items = entity.resumen_liquidos or []

        nominal = 0.0
        retro = 0.0
        sac = 0.0
        otros = 0.0

        if items:
            for item in items:
                liq = item.liquido_pesos
                p_liq = _to_ym(item.periodo_liquidado)
                c_norm = (item.concepto_normalizado or "").lower()
                op = item.orden_pago or item.orden_pago_codigo or ""

                if "sac" in c_norm or "874" in op or "SAC" in op.upper():
                    sac += liq
                elif c_norm == "sueldo":
                    nominal += liq
                elif c_norm == "retroactivo" or (
                    p_liq and mes_pago_norm and p_liq < mes_pago_norm
                ):
                    retro += liq
                elif (p_liq and mes_pago_norm and p_liq == mes_pago_norm) or not p_liq:
                    nominal += liq
                else:
                    otros += liq
        else:
            for liq_seq in entity.liquidaciones:
                liq = liq_seq.liquido_calculado
                p_liq = _to_ym(liq_seq.cargo.periodo_liquidado)
                op = liq_seq.cargo.orden_pago or ""

                if "874" in op or "SAC" in op.upper():
                    sac += liq
                elif p_liq and mes_pago_norm and p_liq < mes_pago_norm:
                    retro += liq
                else:
                    nominal += liq

        total_liquido = round(entity.totales.total_liquido, 2)
        nominal_r = round(nominal, 2)
        retro_r = round(retro, 2)
        sac_r = round(sac, 2)
        otros_r = round(otros, 2)

        # Ajustar únicamente centavos por desvío de redondeo (diff <= 0.05) si el total no coincide exactamente
        suma_desglose = round(nominal_r + retro_r + sac_r + otros_r, 2)
        diff = round(total_liquido - suma_desglose, 2)
        if 0.0 < abs(diff) <= 0.05:
            if nominal_r > 0:
                nominal_r = round(nominal_r + diff, 2)
            elif retro_r > 0:
                retro_r = round(retro_r + diff, 2)

        return DesgloseFinancieroDTO(
            mes_pago=entity.agente.mes_pago,
            total_liquido=total_liquido,
            importe_periodo_nominal=nominal_r,
            importe_retroactivos=retro_r,
            importe_sac=sac_r,
            importe_otros=otros_r,
        )

    @staticmethod
    def to_summary(dto: ReceiptResponseDTO) -> ReceiptSummaryDTO:
        """Proyecta un ReceiptResponseDTO a su resumen reducido de bajo-token."""
        cargos = [liq.cargo for liq in dto.liquidaciones]
        horas_totales = round(sum(c.carga_horaria or 0.0 for c in cargos), 2)
        antiguedades = [
            c.antiguedad_anios for c in cargos if c.antiguedad_anios is not None
        ]
        return ReceiptSummaryDTO(
            total_haberes=dto.totales.total_haberes,
            total_descuentos=dto.totales.total_descuentos,
            neto_a_cobrar=dto.totales.total_liquido,
            periodo=dto.agente.mes_pago,
            cargos=cargos,
            horas_totales=horas_totales,
            antiguedad_max_anios=max(antiguedades) if antiguedades else None,
        )
