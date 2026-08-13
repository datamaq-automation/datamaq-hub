"""Integration tests for gateways with real sample PDF and generic mock."""

from src.adapters.gateways.pdfplumber_extractor_gateway import (
    PdfPlumberExtractorGateway,
)
from src.adapters.gateways.receipt_parsers.dgcye_parser_gateway import (
    DGCyEParserGateway,
)
from src.adapters.gateways.receipt_parsers.generic_parser_gateway import (
    GenericParserGateway,
)
from src.adapters.gateways.receipt_parsers.parser_registry_gateway import (
    ReceiptParserRegistryGateway,
)
from src.domain.recibos.ports import ExtractedPDF, PageData
from src.domain.recibos.value_objects import TipoRecibo


def test_dgcye_gateway_with_real_pdf(sample_pdf_bytes: bytes):
    extractor = PdfPlumberExtractorGateway()
    extracted_pdf = extractor.extract_from_bytes(sample_pdf_bytes)

    registry = ReceiptParserRegistryGateway()
    parser = registry.get_parser(extracted_pdf)

    assert isinstance(parser, DGCyEParserGateway)
    assert parser.can_handle(extracted_pdf) is True

    receipt = parser.parse(extracted_pdf)

    # 1. Structure
    assert receipt.tipo_recibo == TipoRecibo.DGCYE_PBA
    assert receipt.agente.nombre_completo == "BUSTOS AGUSTÍN"
    assert receipt.agente.numero_documento == "36528392"
    assert receipt.agente.cuil == "20-36528392-4"

    # 2. Resumen Líquidos
    assert len(receipt.resumen_liquidos) == 14
    total_resumen = sum(r.liquido_pesos for r in receipt.resumen_liquidos)
    assert round(total_resumen, 2) == 2585423.32

    # 3. Liquidaciones
    assert len(receipt.liquidaciones) == 14
    for liq in receipt.liquidaciones:
        assert len(liq.conceptos) > 0
        assert liq.subtotal_haberes > 0
        assert (
            round(liq.subtotal_haberes - liq.subtotal_descuentos, 2)
            == liq.liquido_calculado
        )

    # 4. Totals
    assert receipt.totales.total_liquido == 2585423.32


def test_generic_gateway_with_mock():
    raw_text = """
    ACME S.A.
    CUIT: 30-71234567-8
    RECIBO DE HABERES
    EMPLEADO: PEREZ JUAN
    CUIL: 20-30123456-3
    CATEGORIA: ADMINISTRATIVO
    PERIODO: 07/2026

    CODIGO CONCEPTO HABERES DESCUENTOS
    001 SUELDO BASICO 500000.00
    002 PRESENTISMO 50000.00
    050 VIATICOS NO REMUNERATIVO 20000.00
    101 JUBILACION 11% 60500.00
    102 OBRA SOCIAL 3% 16500.00
    103 LEY 19032 3% 16500.00

    TOTAL BRUTO: 570000.00
    TOTAL RETENCIONES: 93500.00
    NETO A COBRAR: 476500.00
    """

    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    extracted = ExtractedPDF(
        total_pages=1,
        pages=[
            PageData(
                page_number=1, width=595.0, height=842.0, text=raw_text, lines=lines
            )
        ],
        raw_full_text=raw_text,
        metadata={},
    )

    parser = GenericParserGateway()
    assert parser.can_handle(extracted) is True

    receipt = parser.parse(extracted)
    assert receipt.tipo_recibo == TipoRecibo.GENERICO
    assert receipt.agente.nombre_completo == "PEREZ JUAN"
    assert receipt.agente.cuil == "20-30123456-3"
    assert receipt.totales.total_haberes == 570000.00
    assert receipt.totales.total_descuentos == 93500.00
    assert receipt.totales.total_liquido == 476500.00
