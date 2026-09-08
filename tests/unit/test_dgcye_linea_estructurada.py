import os

import pytest

from src.adapters.gateways.pdfplumber_extractor_gateway import (
    PdfPlumberExtractorGateway,
)
from src.adapters.gateways.receipt_parsers.dgcye_parser_gateway import (
    DGCyEParserGateway,
)
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.domain.recibos.entities import ResumenLiquidoItem
from src.domain.recibos.services import TotalesCalculatorService


def test_lineas_estructuradas_y_cierre_real_pdf() -> None:
    pdf_path = "data/36528392-2026-09-07.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip(f"PDF real fixture '{pdf_path}' no presente en entorno.")

    extractor = PdfPlumberExtractorGateway()
    extracted = extractor.extract_from_path(pdf_path)
    parser = DGCyEParserGateway()
    recibo = parser.parse(extracted)

    # 1. Integridad de Cierre
    assert recibo.totales.estado_cierre == "VALIDO"
    assert recibo.totales.total_declarado == 1584497.13
    assert recibo.totales.total_liquido == 1584497.13
    assert recibo.totales.diferencia_cierre == 0.0

    # 2. Líneas estructuradas
    assert len(recibo.resumen_liquidos) == 11
    sec_016 = [r for r in recibo.resumen_liquidos if r.secuencia == "016"]
    assert len(sec_016) == 2
    assert sec_016[0].distrito == "055"
    assert sec_016[0].tipo_nivel == "IS"
    assert sec_016[0].escuela == "0199"
    assert sec_016[0].revista == "PRO"
    assert sec_016[0].orden_pago == "00871"
    assert sec_016[0].fecha_pago == "07/09/2026"
    assert sec_016[0].importe == 457570.43
    assert sec_016[0].concepto_normalizado == "sueldo"

    assert sec_016[1].importe == 24270.92
    assert sec_016[1].concepto_normalizado == "retroactivo"

    # DTO mapping verification (aditivo, preserva legacy)
    dto = ReceiptMapper.to_dto(recibo)
    assert dto.estado_cierre == "VALIDO"
    assert dto.total_declarado == 1584497.13
    assert dto.resumen_liquidos[0].distrito == "055"
    assert dto.resumen_liquidos[0].tipo_nivel == "IS"
    assert dto.resumen_liquidos[0].concepto_normalizado == "sueldo"


def test_totales_calculator_sin_total() -> None:
    item = ResumenLiquidoItem(
        establecimiento_codigo="055 IS 0199",
        secuencia="001",
        periodo_liquidado="08 / 2026",
        fecha_pago="07/09/2026",
        orden_pago_codigo="00871",
        orden_pago_descripcion="SDOS PRO AGO/2026 CAJ",
        liquido_pesos=100.0,
    )
    totales = TotalesCalculatorService.calculate([], [item], total_declarado=None)
    assert totales.total_liquido == 100.0
    assert totales.estado_cierre == "SIN_TOTAL"
    assert totales.total_declarado is None
