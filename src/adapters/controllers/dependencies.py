"""Dependency injection providers for FastAPI controllers."""

from functools import lru_cache

from src.adapters.gateways.pdfplumber_extractor_gateway import (
    PdfPlumberExtractorGateway,
)
from src.adapters.gateways.receipt_parsers.parser_registry_gateway import (
    ReceiptParserRegistryGateway,
)
from src.application.use_cases.parse_receipt import ParseReceiptUseCase
from src.domain.recibos.ports import PDFExtractorPort, ReceiptParserRegistryPort


@lru_cache
def get_pdf_extractor_gateway() -> PDFExtractorPort:
    return PdfPlumberExtractorGateway()


@lru_cache
def get_parser_registry_gateway() -> ReceiptParserRegistryPort:
    return ReceiptParserRegistryGateway()


def get_parse_receipt_use_case() -> ParseReceiptUseCase:
    extractor = get_pdf_extractor_gateway()
    parser_registry = get_parser_registry_gateway()
    return ParseReceiptUseCase(extractor=extractor, parser_registry=parser_registry)
