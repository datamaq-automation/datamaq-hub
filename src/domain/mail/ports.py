"""Abstract domain ports (interfaces) for mail reading capabilities."""

from typing import Protocol

from src.domain.mail.entities import (
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)


class MailReaderPort(Protocol):
    """Port for read-only email querying operations against an IMAP server."""

    def get_folders(self) -> list[EmailFolder]:
        """Fetch all accessible IMAP folders with counts of total and unread messages."""
        ...

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> tuple[list[EmailSummary], int, int]:
        """List email summaries from a folder.

        Returns:
            Tuple of (messages, total_in_folder, total_unread_in_folder).
        """
        ...

    def get_message_by_uid(self, uid: str, folder: str = "INBOX") -> EmailDetail | None:
        """Fetch full email details by UID in read-only mode without mutating seen status."""
        ...

    def get_unread_summary(
        self, folder: str = "INBOX", limit: int = 5
    ) -> UnreadSummary:
        """Fetch count and brief list of recent unread messages."""
        ...
