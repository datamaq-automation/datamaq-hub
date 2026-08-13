"""Unit and functional tests for the generic receipt parser."""

from src.schemas.recibo import TipoRecibo
from src.services.generic_parser import GenericReceiptParser
from src.services.pdf_extractor import ExtractedPDF, PageData


def test_generic_parser_mock_pdf():
    """Test generic parser logic using an in-memory structured ExtractedPDF."""
    raw_text = """
    ACME S.A.
    CUIT: 30-71234567-8
    RECIBO DE HABERES
    EMPLEADO: PEREZ JUAN
    CUIL: 20-30123456-7
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

    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    extracted = ExtractedPDF(
        total_pages=1,
        pages=[
            PageData(
                page_number=1, width=595.0, height=842.0, text=raw_text, lines=lines
            )
        ],
        raw_full_text=raw_text,
        metadata={"title": "Recibo ACME"},
    )

    parser = GenericReceiptParser()
    assert parser.can_handle(extracted) is True

    response = parser.parse(extracted)
    assert response.tipo_recibo == TipoRecibo.GENERICO
    assert "ACME" in response.empleador.organismo_o_empresa
    assert response.empleador.cuit == "30-71234567-8"
    assert response.agente.nombre_completo == "PEREZ JUAN"
    assert response.agente.cuil == "20-30123456-7"
    assert len(response.liquidaciones) == 1

    liq = response.liquidaciones[0]
    assert len(liq.conceptos) >= 5

    # Totals check
    assert response.totales.total_haberes == 570000.00
    assert response.totales.total_descuentos == 93500.00
    assert response.totales.total_liquido == 476500.00
