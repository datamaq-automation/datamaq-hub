"""Base parser interface and domain exceptions for receipt parsing."""

from abc import ABC, abstractmethod

from src.schemas.recibo import ReciboSueldoResponse
from src.services.pdf_extractor import ExtractedPDF


class ReceiptParsingError(Exception):
    """Domain exception raised when a salary receipt cannot be parsed or data is invalid."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidPDFError(ReceiptParsingError):
    """Exception raised when the PDF document is unreadable or malformed."""


class BaseReceiptParser(ABC):
    """Abstract interface for all specialized salary receipt parsers."""

    @abstractmethod
    def can_handle(self, extracted_pdf: ExtractedPDF) -> bool:
        """Check if this parser can handle the provided extracted PDF."""

    @abstractmethod
    def parse(self, extracted_pdf: ExtractedPDF) -> ReciboSueldoResponse:
        """Parse the extracted PDF into a validated ReciboSueldoResponse schema."""
