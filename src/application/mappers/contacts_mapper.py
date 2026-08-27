"""Mapper between Contact domain entities and Pydantic DTOs."""

from src.application.dtos.contacts_dto import ContactDTO
from src.domain.contacts.entities import Contact


class ContactsMapper:
    """Static mapper for contacts."""

    @staticmethod
    def to_dto(entity: Contact) -> ContactDTO:
        return ContactDTO(
            id_contacto=entity.id_contacto,
            nombre=entity.nombre,
            nombre_pila=entity.nombre_pila,
            apellido=entity.apellido,
            email=entity.email,
            telefono=entity.telefono,
            organizacion=entity.organizacion,
            notas=entity.notas,
            vcard=entity.vcard,
            modificado=entity.modificado,
            cuenta=entity.cuenta,
            grupos=list(entity.grupos),
        )
