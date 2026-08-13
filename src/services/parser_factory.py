"""Parser factory and orchestrator for receipt parsing."""

from src.schemas.recibo import ReciboSueldoResponse
from src.services.base_parser import BaseReceiptParser, ReceiptParsingError
from src.services.dgcye_parser import DGCyEReceiptParser
from src.services.generic_parser import GenericReceiptParser
from src.services.pdf_extractor import ExtractedPDF, PDFExtractorService


class ReceiptParserFactory:
    """Factory to detect receipt format and delegate parsing to the appropriate engine."""

    def __init__(self, parsers: list[BaseReceiptParser] | None = None) -> None:
        self.parsers = parsers or [
            DGCyEReceiptParser(),
            GenericReceiptParser(),
        ]

    def get_parser(self, extracted_pdf: ExtractedPDF) -> BaseReceiptParser:
        """Find the first parser capable of handling the extracted document."""
        for parser in self.parsers:
            if parser.can_handle(extracted_pdf):
                return parser

        raise ReceiptParsingError(
            "Could not identify a matching parser for this document.",
            details={"total_pages": extracted_pdf.total_pages},
        )

    def parse_pdf_bytes(
        self, pdf_bytes: bytes, filename: str = "receipt.pdf"
    ) -> ReciboSueldoResponse:
        """Extract and parse PDF from raw byte stream."""
        extracted = PDFExtractorService.extract_from_bytes(pdf_bytes)
        parser = self.get_parser(extracted)
        response = parser.parse(extracted)
        response.metadata["filename"] = filename
        return response

    def parse_pdf_file(self, file_path: str) -> ReciboSueldoResponse:
        """Extract and parse PDF from local file path."""
        extracted = PDFExtractorService.extract_from_path(file_path)
        parser = self.get_parser(extracted)
        response = parser.parse(extracted)
        response.metadata["filename"] = file_path
        return response
