"""Use case for listing and searching contacts."""

from src.application.dtos.contacts_dto import ContactListResponseDTO
from src.application.mappers.contacts_mapper import ContactsMapper
from src.domain.contacts.ports import ContactsRepositoryPort


class ListContactsUseCase:
    """Use case to search and paginate contacts for an account."""

    def __init__(self, repository: ContactsRepositoryPort) -> None:
        self.repository = repository

    def execute(
        self,
        account: str,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ContactListResponseDTO:
        contacts, total = self.repository.list_contacts(
            account=account,
            query=query,
            limit=limit,
            offset=offset,
        )
        return ContactListResponseDTO(
            total=total,
            cuenta=account,
            contactos=[ContactsMapper.to_dto(c) for c in contacts],
        )
