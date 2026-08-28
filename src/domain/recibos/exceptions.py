"""Domain exceptions for salary receipts domain."""

from typing import Any


class DomainException(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ReceiptParsingError(DomainException):
    """Raised when parsing fails or the format is unrecognized."""


class InvalidPDFError(ReceiptParsingError):
    """Raised when PDF file is invalid, corrupt, or unreadable."""


class InvalidIdentifierError(DomainException):
    """Raised when a CUIT, CUIL, or DNI fails domain validation rules."""


class ReciboNotFoundError(DomainException):
    """Raised when a salary receipt is not found in repository."""
