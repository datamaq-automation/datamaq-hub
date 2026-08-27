"""Use case for creating a new contact."""

from datetime import datetime, timezone

from src.application.dtos.contacts_dto import ContactDTO, CreateContactDTO
from src.application.mappers.contacts_mapper import ContactsMapper
from src.domain.contacts.entities import Contact
from src.domain.contacts.ports import ContactsRepositoryPort
from src.domain.contacts.services import VCardFormatterService


class CreateContactUseCase:
    """Use case to create a new address book contact."""

    def __init__(self, repository: ContactsRepositoryPort) -> None:
        self.repository = repository

    def execute(self, dto: CreateContactDTO, account: str) -> ContactDTO:
        effective_account = dto.cuenta or account
        now_iso = datetime.now(timezone.utc).isoformat()

        # Generate vCard if not provided
        vcard_text = VCardFormatterService.generate_vcard(
            name=dto.nombre,
            firstname=dto.nombre_pila,
            surname=dto.apellido,
            email=dto.email,
            phone=dto.telefono,
            organization=dto.organizacion,
            note=dto.notas,
        )

        contact = Contact(
            id_contacto="",
            nombre=dto.nombre.strip(),
            nombre_pila=dto.nombre_pila.strip(),
            apellido=dto.apellido.strip(),
            email=dto.email.strip().lower(),
            telefono=dto.telefono.strip(),
            organizacion=dto.organizacion.strip(),
            notas=dto.notas.strip(),
            vcard=vcard_text,
            modificado=now_iso,
            eliminado=False,
            cuenta=effective_account,
        )

        created = self.repository.create_contact(
            contact=contact, account=effective_account
        )
        return ContactsMapper.to_dto(created)
