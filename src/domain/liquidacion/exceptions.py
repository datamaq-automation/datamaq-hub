"""Domain exceptions for salary settlement and projection."""

from typing import Any


class LiquidacionDomainException(Exception):
    """Base exception for all domain errors in liquidacion."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DesignacionInvalidaException(LiquidacionDomainException):
    """Raised when designation parameters are invalid or incoherent."""


class NivelCargoInvalidoException(LiquidacionDomainException):
    """Raised when an unknown position level is provided."""


class ParitariaNoEncontradaException(LiquidacionDomainException):
    """Raised when paritary rates for a given period cannot be found."""
