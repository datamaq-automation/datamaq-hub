"""Unit tests for application mappers."""

from src.application.dtos.receipt_dto import ReceiptResponseDTO
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    ConceptoItem,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.value_objects import TipoConcepto, TipoRecibo


def test_receipt_mapper():
    entity = ReciboSueldo(
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(
            organismo_o_empresa="DGCyE PBA",
            dependencia="Administracion",
            cuit="30-62739371-3",
        ),
        agente=Agente(
            nombre_completo="BUSTOS AGUSTÍN",
            tipo_documento="DNI",
            numero_documento="36528392",
            sexo="M",
            cuil="20-36528392-4",
            mes_pago="07 / 2026",
        ),
        resumen_liquidos=[
            ResumenLiquidoItem(
                establecimiento_codigo="055 IS 0199",
                secuencia="016",
                periodo_liquidado="07 / 2026",
                fecha_pago="07/08/2026",
                orden_pago_codigo="00769",
                orden_pago_descripcion="SUELDO",
                liquido_pesos=446146.21,
            )
        ],
        liquidaciones=[
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="IS-0199", distrito="05-TIGRE"
                ),
                cargo=CargoDetalle(secuencia="016", situacion_revista="PROV."),
                conceptos=[
                    ConceptoItem(
                        codigo="0510",
                        descripcion="BASICO",
                        haberes=300000.0,
                        tipo=TipoConcepto.REMUNERATIVO,
                    )
                ],
                subtotal_haberes=300000.0,
                subtotal_descuentos=0.0,
                liquido_calculado=300000.0,
            )
        ],
        totales=TotalesConsolidados(
            total_haberes_remunerativos=300000.0,
            total_haberes_no_remunerativos=0.0,
            total_haberes=300000.0,
            total_descuentos=0.0,
            total_liquido=300000.0,
        ),
        metadata={"filename": "test.pdf"},
    )

    dto = ReceiptMapper.to_dto(entity)
    assert isinstance(dto, ReceiptResponseDTO)
    assert dto.agente.nombre_completo == "BUSTOS AGUSTÍN"
    assert dto.empleador.cuit == "30-62739371-3"
    assert len(dto.resumen_liquidos) == 1
    assert len(dto.liquidaciones) == 1
    assert dto.totales.total_liquido == 300000.0
