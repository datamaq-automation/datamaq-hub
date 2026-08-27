"""Use case for listing IMAP mail folders."""

from src.application.dtos.mail_dto import EmailFolderDTO
from src.application.mappers.mail_mapper import MailMapper
from src.domain.mail.ports import MailReaderPort


class ListMailFoldersUseCase:
    """Orchestrates fetching all IMAP folders and their message statistics."""

    def __init__(self, mail_reader: MailReaderPort) -> None:
        self.mail_reader = mail_reader

    def execute(self) -> list[EmailFolderDTO]:
        """Executes the folder listing."""
        folders = self.mail_reader.get_folders()
        return [MailMapper.to_folder_dto(f) for f in folders]
