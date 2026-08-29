"""Domain exceptions for email operations."""

from typing import Any


class MailDomainException(Exception):
    """Base exception for all mail domain errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmailNotFoundError(MailDomainException):
    """Raised when an email message with the given UID is not found."""

    def __init__(self, uid: str, folder: str = "INBOX") -> None:
        super().__init__(
            f"No se encontró el correo con UID '{uid}' en la carpeta '{folder}'."
        )
        self.uid = uid
        self.folder = folder


class MailboxNotFoundError(MailDomainException):
    """Raised when an IMAP folder or mailbox does not exist."""

    def __init__(self, folder: str) -> None:
        super().__init__(f"La carpeta de correo '{folder}' no existe en el servidor.")
        self.folder = folder


class MailConnectionError(MailDomainException):
    """Raised when a connection to the IMAP server cannot be established or times out."""

    def __init__(self, host: str, port: int, details: str = "") -> None:
        msg = f"No se pudo conectar al servidor IMAP en {host}:{port}."
        if details:
            msg += f" Detalle: {details}"
        super().__init__(msg)
        self.host = host
        self.port = port
        self.details = details


class MailAuthenticationError(MailDomainException):
    """Raised when IMAP authentication fails."""

    def __init__(self, user: str, details: str = "") -> None:
        msg = f"Falla de autenticación en el servidor IMAP para el usuario '{user}'."
        if details:
            msg += f" Detalle: {details}"
        super().__init__(msg)
        self.user = user
        self.details = details


class InvalidEmailAddressError(MailDomainException):
    """Raised when an email address format is invalid."""

    def __init__(self, address: str) -> None:
        super().__init__(
            f"La dirección de correo '{address}' no tiene un formato válido."
        )
        self.address = address


class AccountNotFoundError(MailDomainException):
    """Raised when a requested mail account is not configured."""

    def __init__(
        self, account: str, available_accounts: list[str] | None = None
    ) -> None:
        disponibles = available_accounts or []
        msg = f"La cuenta de correo '{account}' no está configurada en el sistema."
        if disponibles:
            msg += f" Cuentas disponibles: {disponibles}"
        super().__init__(msg)
        self.account = account
        self.available_accounts = disponibles
        self.details: dict[str, Any] | None = (
            {"cuentas_disponibles": disponibles} if disponibles else None
        )
