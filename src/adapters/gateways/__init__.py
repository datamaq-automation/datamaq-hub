"""Gateways package."""

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

__all__ = [
    "DGCyEParserGateway",
    "GenericParserGateway",
    "PdfPlumberExtractorGateway",
    "ReceiptParserRegistryGateway",
]
