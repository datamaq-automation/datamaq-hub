from typing import Any

from src.application.dtos.common_dto import ErrorDetailDTO, ErrorResponseDTO
from src.domain.calendar.exceptions import (
    CalendarDomainException,
    CalendarNotFoundError,
    EventNotFoundError,
    ScheduleConflictError,
)
from src.domain.contacts.exceptions import (
    ContactNotFoundError,
    ContactsDomainException,
)
from src.domain.horarios_docencia.exceptions import (
    HorariosDocenciaDomainException,
    IncompatibilidadHorariaCriticaException,
)
from src.domain.leads.exceptions import (
    LeadException,
    LeadValidationException,
)
from src.domain.liquidacion.exceptions import LiquidacionDomainException
from src.domain.mail.exceptions import (
    EmailNotFoundError,
    MailAuthenticationError,
    MailboxNotFoundError,
    MailConnectionError,
    MailDomainException,
)
from src.domain.recibos.exceptions import (
    DomainException,
    InvalidIdentifierError,
    InvalidPDFError,
    ReceiptParsingError,
    ReciboNotFoundError,
)


class ErrorPresenter:
    """Formats domain and validation exceptions into standardized error DTOs."""

    @staticmethod
    def format_domain_error(
        exc: DomainException
        | LiquidacionDomainException
        | HorariosDocenciaDomainException
        | MailDomainException
        | ContactsDomainException
        | CalendarDomainException
        | LeadException,
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
        elif isinstance(exc, ReciboNotFoundError):
            code_name = "RECIBO_NOT_FOUND"
            status_code = 404
        elif isinstance(exc, InvalidIdentifierError):
            code_name = "INVALID_IDENTIFIER_ERROR"
            status_code = 422
        elif isinstance(exc, LiquidacionDomainException):
            code_name = "LIQUIDACION_DOMAIN_ERROR"
            status_code = 422
        elif isinstance(exc, IncompatibilidadHorariaCriticaException):
            code_name = "INCOMPATIBILIDAD_HORARIA_CRITICA"
            status_code = 409
        elif isinstance(exc, HorariosDocenciaDomainException):
            code_name = "HORARIOS_DOCENCIA_DOMAIN_ERROR"
            status_code = 422
        elif isinstance(exc, EmailNotFoundError):
            code_name = "EMAIL_NOT_FOUND"
            status_code = 404
        elif isinstance(exc, MailboxNotFoundError):
            code_name = "MAILBOX_NOT_FOUND"
            status_code = 404
        elif isinstance(exc, MailAuthenticationError):
            code_name = "MAIL_AUTHENTICATION_ERROR"
            status_code = 401
        elif isinstance(exc, MailConnectionError):
            code_name = "MAIL_CONNECTION_ERROR"
            status_code = 502
        elif isinstance(exc, MailDomainException):
            code_name = "MAIL_DOMAIN_ERROR"
            status_code = 422
        elif isinstance(exc, ContactNotFoundError):
            code_name = "CONTACT_NOT_FOUND"
            status_code = 404
        elif isinstance(exc, ContactsDomainException):
            code_name = "CONTACTS_DOMAIN_ERROR"
            status_code = 422
        elif isinstance(exc, EventNotFoundError):
            code_name = "EVENT_NOT_FOUND"
            status_code = 404
        elif isinstance(exc, CalendarNotFoundError):
            code_name = "CALENDAR_NOT_FOUND"
            status_code = 404
        elif isinstance(exc, ScheduleConflictError):
            code_name = "SCHEDULE_CONFLICT_ERROR"
            status_code = 409
        elif isinstance(exc, CalendarDomainException):
            code_name = "CALENDAR_DOMAIN_ERROR"
            status_code = 422
        elif isinstance(exc, LeadValidationException):
            code_name = "LEAD_VALIDATION_ERROR"
            status_code = 422
        elif isinstance(exc, LeadException):
            code_name = "LEAD_DOMAIN_ERROR"
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
