"""Pure transport-agnostic controller for mail reader operations."""

from src.application.dtos.mail_dto import (
    EmailDetailDTO,
    EmailFolderDTO,
    MailInboxResponseDTO,
    UnreadSummaryDTO,
)
from src.application.use_cases.get_mail_detail import GetMailDetailUseCase
from src.application.use_cases.get_unread_summary import GetUnreadSummaryUseCase
from src.application.use_cases.list_inbox_messages import ListInboxMessagesUseCase
from src.application.use_cases.list_mail_folders import ListMailFoldersUseCase


class MailController:
    """Agnostic controller orchestrating email querying use cases."""

    def __init__(
        self,
        list_folders_use_case: ListMailFoldersUseCase,
        list_inbox_use_case: ListInboxMessagesUseCase,
        get_mail_detail_use_case: GetMailDetailUseCase,
        get_unread_summary_use_case: GetUnreadSummaryUseCase,
    ) -> None:
        self.list_folders_use_case = list_folders_use_case
        self.list_inbox_use_case = list_inbox_use_case
        self.get_mail_detail_use_case = get_mail_detail_use_case
        self.get_unread_summary_use_case = get_unread_summary_use_case

    def get_folders(self) -> list[EmailFolderDTO]:
        """Queries and returns all accessible IMAP folders with statistics."""
        return self.list_folders_use_case.execute()

    def get_inbox_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        sin_leer: bool = False,
        q: str | None = None,
    ) -> MailInboxResponseDTO:
        """Queries messages from folder with pagination and filters."""
        return self.list_inbox_use_case.execute(
            folder=folder,
            limit=limit,
            offset=offset,
            unread_only=sin_leer,
            q=q,
        )

    def get_unread_summary(
        self,
        folder: str = "INBOX",
        limit: int = 5,
        q: str | None = None,
    ) -> UnreadSummaryDTO:
        """Queries quick unread messages summary."""
        return self.get_unread_summary_use_case.execute(
            folder=folder,
            limit=limit,
            q=q,
        )

    def get_message_detail(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetailDTO:
        """Queries full email detail by UID."""
        return self.get_mail_detail_use_case.execute(
            uid=uid,
            folder=folder,
            include_html=include_html,
            max_chars=max_chars,
        )
