"""Unit tests for domain services."""

from src.domain.recibos.entities import (
    CargoDetalle,
    ConceptoItem,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ResumenLiquidoItem,
)
from src.domain.recibos.services import (
    TextNormalizerService,
    TotalesCalculatorService,
)
from src.domain.recibos.value_objects import TipoConcepto


def test_text_normalizer_service():
    assert TextNormalizerService.normalize("  JUAN  PEREZ  ") == "JUAN PEREZ"
    assert (
        TextNormalizerService.normalize("ESCUELA DE EDUCACI?N")
        == "ESCUELA DE EDUCACIÓN"
    )
    assert (
        TextNormalizerService.normalize("ESCUELA DE EDUCACIÓ") == "ESCUELA DE EDUCACIÓN"
    )
    assert TextNormalizerService.normalize(None) == ""


def test_totales_calculator_service():
    estab = EstablecimientoDetalle(codigo="001")
    cargo = CargoDetalle(secuencia="001")

    liq = LiquidacionSecuencia(
        establecimiento=estab,
        cargo=cargo,
        conceptos=[
            ConceptoItem(
                codigo="0510",
                descripcion="BASICO",
                haberes=1000.0,
                descuentos=None,
                tipo=TipoConcepto.REMUNERATIVO,
            ),
            ConceptoItem(
                codigo="2575",
                descripcion="FONID",
                haberes=200.0,
                descuentos=None,
                tipo=TipoConcepto.NO_REMUNERATIVO,
            ),
            ConceptoItem(
                codigo="1060",
                descripcion="IPS",
                haberes=None,
                descuentos=150.0,
                tipo=TipoConcepto.DESCUENTO,
            ),
        ],
        subtotal_haberes=1200.0,
        subtotal_descuentos=150.0,
        liquido_calculado=1050.0,
    )

    totales = TotalesCalculatorService.calculate(
        liquidaciones=[liq],
        resumen_liquidos=[
            ResumenLiquidoItem(
                establecimiento_codigo="001",
                secuencia="001",
                periodo_liquidado="07/2026",
                fecha_pago="01/08/2026",
                orden_pago_codigo="1",
                orden_pago_descripcion="SUELDO",
                liquido_pesos=1050.0,
            )
        ],
    )

    assert totales.total_haberes_remunerativos == 1000.0
    assert totales.total_haberes_no_remunerativos == 200.0
    assert totales.total_haberes == 1200.0
    assert totales.total_descuentos == 150.0
    assert totales.total_liquido == 1050.0
