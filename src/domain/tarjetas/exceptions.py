"""Excepciones de dominio para tarjetas de crédito."""

from typing import Any


class TarjetaException(Exception):
    """Excepción base para todos los errores del dominio de tarjetas de crédito."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TarjetaParserException(TarjetaException):
    """Se lanza cuando falla el parseo de un resumen de tarjeta de crédito."""
