"""Use case for deleting a contact."""

from src.domain.contacts.exceptions import ContactNotFoundError
from src.domain.contacts.ports import ContactsRepositoryPort


class DeleteContactUseCase:
    """Use case to delete (soft-delete) a contact."""

    def __init__(self, repository: ContactsRepositoryPort) -> None:
        self.repository = repository

    def execute(self, contact_id: str, account: str) -> bool:
        existing = self.repository.get_contact_by_id(
            contact_id=contact_id, account=account
        )
        if not existing:
            raise ContactNotFoundError(contact_id=contact_id, account=account)

        return self.repository.delete_contact(contact_id=contact_id, account=account)
