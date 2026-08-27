"""Presenter for mapping and formatting error responses."""

from typing import Any

from src.application.dtos.common_dto import ErrorDetailDTO, ErrorResponseDTO
from src.domain.horarios_docencia.exceptions import (
    HorariosDocenciaDomainException,
)
from src.domain.liquidacion.exceptions import LiquidacionDomainException
from src.domain.recibos.exceptions import (
    DomainException,
    InvalidIdentifierError,
    InvalidPDFError,
    ReceiptParsingError,
)


class ErrorPresenter:
    """Formats domain and validation exceptions into standardized error DTOs."""

    @staticmethod
    def format_domain_error(
        exc: DomainException
        | LiquidacionDomainException
        | HorariosDocenciaDomainException,
        default_status_code: int = 422,
    ) -> tuple[ErrorResponseDTO, int]:
        status_code = default_status_code
        code_name = "DOMAIN_ERROR"

        if isinstance(exc, InvalidPDFError):
            code_name = "INVALID_PDF_ERROR"
            status_code = 400
        elif isinstance(exc, ReceiptParsingError):
            code_name = "RECEIPT_PARSING_ERROR"
            status_code = 422
        elif isinstance(exc, InvalidIdentifierError):
            code_name = "INVALID_IDENTIFIER_ERROR"
            status_code = 422
        elif isinstance(exc, LiquidacionDomainException):
            code_name = "LIQUIDACION_DOMAIN_ERROR"
            status_code = 422
        elif isinstance(exc, HorariosDocenciaDomainException):
            code_name = "HORARIOS_DOCENCIA_DOMAIN_ERROR"
            status_code = 422

        msg = getattr(exc, "message", str(exc))
        details = getattr(exc, "details", None)

        payload = ErrorResponseDTO(
            success=False,
            error=ErrorDetailDTO(
                code=code_name,
                message=msg,
                details=details,
            ),
        )
        return payload, status_code

    @staticmethod
    def format_generic_error(
        message: str,
        code: str = "BAD_REQUEST",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> tuple[ErrorResponseDTO, int]:
        payload = ErrorResponseDTO(
            success=False,
            error=ErrorDetailDTO(
                code=code,
                message=message,
                details=details,
            ),
        )
        return payload, status_code
