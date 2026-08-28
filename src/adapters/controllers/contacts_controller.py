"""Controller for contacts operations agnostics of transport layer."""

from src.application.dtos.contacts_dto import (
    ContactDTO,
    ContactListResponseDTO,
    CreateContactDTO,
    UpdateContactDTO,
)
from src.application.use_cases.create_contact import CreateContactUseCase
from src.application.use_cases.delete_contact import DeleteContactUseCase
from src.application.use_cases.exportar_contactos_vcard import (
    ExportarContactosVCardUseCase,
)
from src.application.use_cases.get_contact_detail import GetContactDetailUseCase
from src.application.use_cases.list_contacts import ListContactsUseCase
from src.application.use_cases.update_contact import UpdateContactUseCase


class ContactsController:
    """Agnostic controller orchestrating address book use cases."""

    def __init__(
        self,
        list_contacts_use_case: ListContactsUseCase,
        get_contact_detail_use_case: GetContactDetailUseCase,
        create_contact_use_case: CreateContactUseCase,
        update_contact_use_case: UpdateContactUseCase,
        delete_contact_use_case: DeleteContactUseCase,
        export_vcard_use_case: ExportarContactosVCardUseCase | None = None,
    ) -> None:
        self._list_contacts = list_contacts_use_case
        self._get_contact = get_contact_detail_use_case
        self._create_contact = create_contact_use_case
        self._update_contact = update_contact_use_case
        self._delete_contact = delete_contact_use_case
        self._export_vcard = export_vcard_use_case

    def list_contacts(
        self,
        account: str,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ContactListResponseDTO:
        return self._list_contacts.execute(
            account=account, query=query, limit=limit, offset=offset
        )

    def get_contact_detail(self, contact_id: str, account: str) -> ContactDTO:
        return self._get_contact.execute(contact_id=contact_id, account=account)

    def create_contact(self, dto: CreateContactDTO, account: str) -> ContactDTO:
        return self._create_contact.execute(dto=dto, account=account)

    def update_contact(
        self, contact_id: str, dto: UpdateContactDTO, account: str
    ) -> ContactDTO:
        return self._update_contact.execute(
            contact_id=contact_id, dto=dto, account=account
        )

    def delete_contact(self, contact_id: str, account: str) -> bool:
        return self._delete_contact.execute(contact_id=contact_id, account=account)

    def export_vcard(self, account: str = "") -> str:
        if not self._export_vcard:
            raise RuntimeError("ExportarContactosVCardUseCase no está configurado.")
        return self._export_vcard.execute(account=account)
