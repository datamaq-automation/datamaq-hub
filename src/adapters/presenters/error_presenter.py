"""Presenter for mapping and formatting error responses."""

from typing import Any

from fastapi.responses import JSONResponse

from src.application.dtos.common_dto import ErrorDetailDTO, ErrorResponseDTO
from src.domain.recibos.exceptions import (
    DomainException,
    InvalidIdentifierError,
    InvalidPDFError,
    ReceiptParsingError,
)


class ErrorPresenter:
    """Formats domain and validation exceptions into standardized JSON responses."""

    @staticmethod
    def format_domain_error(
        exc: DomainException, status_code: int = 422
    ) -> JSONResponse:
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

        payload = ErrorResponseDTO(
            success=False,
            error=ErrorDetailDTO(
                code=code_name,
                message=exc.message,
                details=exc.details,
            ),
        )
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @staticmethod
    def format_generic_error(
        message: str,
        code: str = "BAD_REQUEST",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> JSONResponse:
        payload = ErrorResponseDTO(
            success=False,
            error=ErrorDetailDTO(
                code=code,
                message=message,
                details=details,
            ),
        )
        return JSONResponse(status_code=status_code, content=payload.model_dump())
