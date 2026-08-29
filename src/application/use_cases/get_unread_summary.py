"""Use case for fetching quick summary of unread email messages."""

from src.application.dtos.mail_dto import UnreadSummaryDTO
from src.application.mappers.mail_mapper import MailMapper
from src.domain.mail.ports import MailReaderPort


class GetUnreadSummaryUseCase:
    """Orchestrates retrieving count and short preview of latest unread emails."""

    def __init__(self, mail_reader: MailReaderPort) -> None:
        self.mail_reader = mail_reader

    def execute(
        self, folder: str = "INBOX", limit: int = 5, q: str | None = None
    ) -> UnreadSummaryDTO:
        """Executes unread summary query."""
        safe_limit = max(1, min(limit, 50))
        summary = self.mail_reader.get_unread_summary(
            folder=folder, limit=safe_limit, q=q
        )
        return MailMapper.to_unread_summary_dto(summary)
