"""Registry gateway implementing ReceiptParserRegistryPort."""

from src.adapters.gateways.receipt_parsers.dgcye_parser_gateway import (
    DGCyEParserGateway,
)
from src.adapters.gateways.receipt_parsers.generic_parser_gateway import (
    GenericParserGateway,
)
from src.domain.recibos.exceptions import ReceiptParsingError
from src.domain.recibos.ports import (
    ExtractedPDF,
    ReceiptParserPort,
    ReceiptParserRegistryPort,
)


class ReceiptParserRegistryGateway(ReceiptParserRegistryPort):
    """Resolves matching ReceiptParserPort according to document structure."""

    def __init__(self, parsers: list[ReceiptParserPort] | None = None) -> None:
        self.parsers = parsers or [
            DGCyEParserGateway(),
            GenericParserGateway(),
        ]

    def get_parser(self, extracted_pdf: ExtractedPDF) -> ReceiptParserPort:
        for parser in self.parsers:
            if parser.can_handle(extracted_pdf):
                return parser

        raise ReceiptParsingError(
            "Could not identify a matching parser for this salary receipt.",
            details={"total_pages": extracted_pdf.total_pages},
        )
