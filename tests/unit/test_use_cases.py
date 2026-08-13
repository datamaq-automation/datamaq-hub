"""Unit tests for application use cases."""

from unittest.mock import MagicMock

from src.application.use_cases.parse_receipt import ParseReceiptUseCase
from src.domain.recibos.entities import (
    Agente,
    Empleador,
    ReciboSueldo,
    TotalesConsolidados,
)
from src.domain.recibos.ports import (
    ExtractedPDF,
    PDFExtractorPort,
    ReceiptParserPort,
    ReceiptParserRegistryPort,
)
from src.domain.recibos.value_objects import TipoRecibo


def test_parse_receipt_use_case():
    mock_extractor = MagicMock(spec=PDFExtractorPort)
    mock_parser_registry = MagicMock(spec=ReceiptParserRegistryPort)
    mock_parser = MagicMock(spec=ReceiptParserPort)

    dummy_extracted = ExtractedPDF(
        total_pages=1,
        pages=[],
        raw_full_text="dummy text",
        metadata={},
    )
    dummy_entity = ReciboSueldo(
        tipo_recibo=TipoRecibo.GENERICO,
        empleador=Empleador(organismo_o_empresa="Mock Co"),
        agente=Agente(
            nombre_completo="TEST USER",
            tipo_documento="DNI",
            numero_documento="12345678",
            cuil="20-12345678-9",
            mes_pago="07/2026",
        ),
        resumen_liquidos=[],
        liquidaciones=[],
        totales=TotalesConsolidados(total_liquido=50000.0),
        metadata={},
    )

    mock_extractor.extract_from_bytes.return_value = dummy_extracted
    mock_parser_registry.get_parser.return_value = mock_parser
    mock_parser.parse.return_value = dummy_entity

    use_case = ParseReceiptUseCase(
        extractor=mock_extractor,
        parser_registry=mock_parser_registry,
    )

    dto = use_case.execute_bytes(b"%PDF-mock", filename="sample.pdf")

    assert dto.agente.nombre_completo == "TEST USER"
    assert dto.totales.total_liquido == 50000.0
    assert dto.metadata["filename"] == "sample.pdf"

    mock_extractor.extract_from_bytes.assert_called_once_with(b"%PDF-mock")
    mock_parser_registry.get_parser.assert_called_once_with(dummy_extracted)
    mock_parser.parse.assert_called_once_with(dummy_extracted)
