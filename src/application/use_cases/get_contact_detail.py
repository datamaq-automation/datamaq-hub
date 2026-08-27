"""Use case for retrieving a contact detail by identifier."""

from src.application.dtos.contacts_dto import ContactDTO
from src.application.mappers.contacts_mapper import ContactsMapper
from src.domain.contacts.exceptions import ContactNotFoundError
from src.domain.contacts.ports import ContactsRepositoryPort


class GetContactDetailUseCase:
    """Use case to get full details of a contact."""

    def __init__(self, repository: ContactsRepositoryPort) -> None:
        self.repository = repository

    def execute(self, contact_id: str, account: str) -> ContactDTO:
        contact = self.repository.get_contact_by_id(
            contact_id=contact_id, account=account
        )
        if not contact:
            raise ContactNotFoundError(contact_id=contact_id, account=account)
        return ContactsMapper.to_dto(contact)
