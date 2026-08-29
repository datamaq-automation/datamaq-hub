"""Abstract domain ports (interfaces) for mail reading capabilities."""

from typing import Protocol

from src.domain.mail.entities import (
    AnalisisEmail,
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)


class MailReaderPort(Protocol):
    """Port for read-only email querying operations against an IMAP server or Gmail REST API."""

    def get_folders(self) -> list[EmailFolder]:
        """Fetch all accessible IMAP folders or Gmail labels with counts of total and unread messages."""
        ...

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[EmailSummary], int, int]:
        """List email summaries from a folder.

        Returns:
            Tuple of (messages, total_in_folder, total_unread_in_folder).
        """
        ...

    def get_message_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        """Fetch full email details by UID in read-only mode without mutating seen status."""
        ...

    def get_unread_summary(
        self,
        folder: str = "INBOX",
        limit: int = 5,
        q: str | None = None,
    ) -> UnreadSummary:
        """Fetch count and brief list of recent unread messages."""
        ...


class MailNotifierPort(Protocol):
    """Abstracción para despachar alertas de oportunidad de correo a canales externos."""

    def notificar_oportunidad_email(
        self, analisis: AnalisisEmail, email: EmailDetail
    ) -> bool:
        """Retorna True si la notificación fue entregada con éxito."""
        ...
