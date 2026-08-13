"""Unit tests for domain entities."""

from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    ConceptoItem,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    TotalesConsolidados,
)
from src.domain.recibos.value_objects import TipoConcepto, TipoRecibo


def test_entities_instantiation():
    agente = Agente(
        nombre_completo="BUSTOS AGUSTÍN",
        tipo_documento="DNI",
        numero_documento="36528392",
        sexo="M",
        cuil="20-36528392-4",
        mes_pago="07 / 2026",
    )
    assert agente.nombre_completo == "BUSTOS AGUSTÍN"

    empleador = Empleador(
        organismo_o_empresa="DGCyE",
        dependencia="DIRECCION GENERAL DE ADMINISTRACION",
        cuit="30-62739371-3",
    )
    assert empleador.cuit == "30-62739371-3"

    concepto = ConceptoItem(
        codigo="0510",
        descripcion="BASICO",
        haberes=300000.00,
        descuentos=None,
        tipo=TipoConcepto.REMUNERATIVO,
    )
    assert concepto.tipo == TipoConcepto.REMUNERATIVO

    cargo = CargoDetalle(
        secuencia="016",
        situacion_revista="PROV.",
        cargo_real="SM",
        carga_horaria=7.0,
    )
    assert cargo.secuencia == "016"

    estab = EstablecimientoDetalle(
        codigo="IS-0199",
        distrito="05-TIGRE",
        categoria="IS-0199",
    )
    assert estab.distrito == "05-TIGRE"

    liq = LiquidacionSecuencia(
        establecimiento=estab,
        cargo=cargo,
        conceptos=[concepto],
        subtotal_haberes=300000.00,
        subtotal_descuentos=0.0,
        liquido_calculado=300000.00,
    )
    assert liq.liquido_calculado == 300000.00

    recibo = ReciboSueldo(
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=empleador,
        agente=agente,
        resumen_liquidos=[],
        liquidaciones=[liq],
        totales=TotalesConsolidados(
            total_haberes_remunerativos=300000.00,
            total_haberes_no_remunerativos=0.0,
            total_haberes=300000.00,
            total_descuentos=0.0,
            total_liquido=300000.00,
        ),
    )
    assert recibo.totales.total_liquido == 300000.00
