"""Use case for updating an existing contact."""

from datetime import datetime, timezone

from src.application.dtos.contacts_dto import ContactDTO, UpdateContactDTO
from src.application.mappers.contacts_mapper import ContactsMapper
from src.domain.contacts.entities import Contact
from src.domain.contacts.exceptions import ContactNotFoundError
from src.domain.contacts.ports import ContactsRepositoryPort
from src.domain.contacts.services import VCardFormatterService


class UpdateContactUseCase:
    """Use case to update contact attributes preserving untouched values."""

    def __init__(self, repository: ContactsRepositoryPort) -> None:
        self.repository = repository

    def execute(
        self, contact_id: str, dto: UpdateContactDTO, account: str
    ) -> ContactDTO:
        existing = self.repository.get_contact_by_id(
            contact_id=contact_id, account=account
        )
        if not existing:
            raise ContactNotFoundError(contact_id=contact_id, account=account)

        now_iso = datetime.now(timezone.utc).isoformat()
        nombre = dto.nombre.strip() if dto.nombre is not None else existing.nombre
        nombre_pila = (
            dto.nombre_pila.strip()
            if dto.nombre_pila is not None
            else existing.nombre_pila
        )
        apellido = (
            dto.apellido.strip() if dto.apellido is not None else existing.apellido
        )
        email = dto.email.strip().lower() if dto.email is not None else existing.email
        telefono = (
            dto.telefono.strip() if dto.telefono is not None else existing.telefono
        )
        organizacion = (
            dto.organizacion.strip()
            if dto.organizacion is not None
            else existing.organizacion
        )
        notas = dto.notas.strip() if dto.notas is not None else existing.notas

        vcard_text = VCardFormatterService.generate_vcard(
            name=nombre,
            firstname=nombre_pila,
            surname=apellido,
            email=email,
            phone=telefono,
            organization=organizacion,
            note=notas,
        )

        updated_entity = Contact(
            id_contacto=existing.id_contacto,
            nombre=nombre,
            nombre_pila=nombre_pila,
            apellido=apellido,
            email=email,
            telefono=telefono,
            organizacion=organizacion,
            notas=notas,
            vcard=vcard_text,
            modificado=now_iso,
            eliminado=existing.eliminado,
            cuenta=existing.cuenta,
            grupos=existing.grupos,
        )

        saved = self.repository.update_contact(contact=updated_entity, account=account)
        return ContactsMapper.to_dto(saved)
