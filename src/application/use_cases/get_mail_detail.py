"""Use case for fetching complete email details by UID."""

from src.application.dtos.mail_dto import EmailDetailDTO
from src.application.mappers.mail_mapper import MailMapper
from src.domain.mail.exceptions import EmailNotFoundError
from src.domain.mail.ports import MailReaderPort


class GetMailDetailUseCase:
    """Orchestrates retrieving full email content and attachment metadata by UID."""

    def __init__(self, mail_reader: MailReaderPort) -> None:
        self.mail_reader = mail_reader

    def execute(self, uid: str, folder: str = "INBOX") -> EmailDetailDTO:
        """Fetches email details or raises EmailNotFoundError if message does not exist."""
        detail = self.mail_reader.get_message_by_uid(uid=uid, folder=folder)
        if detail is None:
            raise EmailNotFoundError(uid=uid, folder=folder)
        return MailMapper.to_detail_dto(detail)
