"""Use case for querying and paginating email messages from a folder."""

from src.application.dtos.mail_dto import MailInboxResponseDTO
from src.application.mappers.mail_mapper import MailMapper
from src.domain.mail.ports import MailReaderPort


class ListInboxMessagesUseCase:
    """Orchestrates querying email message summaries with pagination and unread filters."""

    def __init__(self, mail_reader: MailReaderPort) -> None:
        self.mail_reader = mail_reader

    def execute(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> MailInboxResponseDTO:
        """Executes message listing and returns paginated DTO response."""
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        messages, total_in_folder, total_unread = self.mail_reader.list_messages(
            folder=folder,
            limit=safe_limit,
            offset=safe_offset,
            unread_only=unread_only,
            q=q,
        )

        dtos = [MailMapper.to_summary_dto(m) for m in messages]
        return MailInboxResponseDTO(
            carpeta=folder,
            total=total_in_folder,
            no_leidos=total_unread,
            offset=safe_offset,
            limit=safe_limit,
            correos=dtos,
        )
