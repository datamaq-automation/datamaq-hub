"""Domain exceptions for contacts bounded context."""


class ContactsDomainException(Exception):
    """Base exception for all contacts domain errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ContactNotFoundError(ContactsDomainException):
    """Raised when a requested contact is not found."""

    def __init__(self, contact_id: str, account: str) -> None:
        super().__init__(
            f"No se encontró el contacto '{contact_id}' para la cuenta '{account}'."
        )
        self.contact_id = contact_id
        self.account = account


class InvalidContactDataError(ContactsDomainException):
    """Raised when contact attributes fail domain validation."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Datos de contacto inválidos: {reason}")
        self.reason = reason
