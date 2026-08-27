"""Unit tests for contacts use cases."""

import pytest

from src.application.dtos.contacts_dto import CreateContactDTO, UpdateContactDTO
from src.application.use_cases.create_contact import CreateContactUseCase
from src.application.use_cases.delete_contact import DeleteContactUseCase
from src.application.use_cases.get_contact_detail import GetContactDetailUseCase
from src.application.use_cases.list_contacts import ListContactsUseCase
from src.application.use_cases.update_contact import UpdateContactUseCase
from src.domain.contacts.entities import Contact, ContactGroup
from src.domain.contacts.exceptions import ContactNotFoundError
from src.domain.contacts.ports import ContactsRepositoryPort


class FakeContactsRepository(ContactsRepositoryPort):
    """In-memory mock repository implementing ContactsRepositoryPort."""

    def __init__(self) -> None:
        self.contacts: dict[str, Contact] = {
            "1": Contact(
                id_contacto="1",
                nombre="Agustín Deoz",
                nombre_pila="Agustín",
                apellido="Deoz",
                email="agustin@datamaq.com.ar",
                telefono="+54 11 1234-5678",
                organizacion="DataMaq",
                notas="Socio",
                vcard="",
                modificado="2026-08-27T10:00:00",
                eliminado=False,
                cuenta="openclaw@datamaq.com.ar",
                grupos=[],
            ),
            "2": Contact(
                id_contacto="2",
                nombre="Laura Fernández",
                nombre_pila="Laura",
                apellido="Fernández",
                email="laura@cliente.com",
                telefono="+54 11 5555-4444",
                organizacion="Cliente SRL",
                notas="Compras",
                vcard="",
                modificado="2026-08-27T10:00:00",
                eliminado=False,
                cuenta="openclaw@datamaq.com.ar",
                grupos=[],
            ),
        }
        self.next_id = 3

    def list_contacts(
        self,
        account: str,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contact], int]:
        filtered = [
            c for c in self.contacts.values() if c.cuenta == account and not c.eliminado
        ]
        if query:
            q = query.lower()
            filtered = [
                c
                for c in filtered
                if q in c.nombre.lower()
                or q in c.email.lower()
                or q in c.organizacion.lower()
            ]
        sliced = filtered[offset : offset + limit]
        return sliced, len(filtered)

    def get_contact_by_id(self, contact_id: str, account: str) -> Contact | None:
        c = self.contacts.get(contact_id)
        if c and c.cuenta == account and not c.eliminado:
            return c
        return None

    def create_contact(self, contact: Contact, account: str) -> Contact:
        cid = str(self.next_id)
        self.next_id += 1
        new_c = Contact(
            id_contacto=cid,
            nombre=contact.nombre,
            nombre_pila=contact.nombre_pila,
            apellido=contact.apellido,
            email=contact.email,
            telefono=contact.telefono,
            organizacion=contact.organizacion,
            notas=contact.notas,
            vcard=contact.vcard,
            modificado=contact.modificado,
            eliminado=False,
            cuenta=account,
            grupos=contact.grupos,
        )
        self.contacts[cid] = new_c
        return new_c

    def update_contact(self, contact: Contact, account: str) -> Contact:
        self.contacts[contact.id_contacto] = contact
        return contact

    def delete_contact(self, contact_id: str, account: str) -> bool:
        c = self.contacts.get(contact_id)
        if c and c.cuenta == account:
            self.contacts[contact_id] = Contact(
                id_contacto=c.id_contacto,
                nombre=c.nombre,
                nombre_pila=c.nombre_pila,
                apellido=c.apellido,
                email=c.email,
                telefono=c.telefono,
                organizacion=c.organizacion,
                notas=c.notas,
                vcard=c.vcard,
                modificado=c.modificado,
                eliminado=True,
                cuenta=c.cuenta,
                grupos=c.grupos,
            )
            return True
        return False

    def list_groups(self, account: str) -> list[ContactGroup]:
        return []


def test_list_contacts_use_case():
    repo = FakeContactsRepository()
    use_case = ListContactsUseCase(repository=repo)

    res = use_case.execute(account="openclaw@datamaq.com.ar", limit=10)
    assert res.total == 2
    assert len(res.contactos) == 2

    # Query search
    res_q = use_case.execute(account="openclaw@datamaq.com.ar", query="Laura")
    assert res_q.total == 1
    assert res_q.contactos[0].nombre == "Laura Fernández"


def test_get_contact_detail_use_case():
    repo = FakeContactsRepository()
    use_case = GetContactDetailUseCase(repository=repo)

    contact = use_case.execute(contact_id="1", account="openclaw@datamaq.com.ar")
    assert contact.id_contacto == "1"
    assert contact.nombre == "Agustín Deoz"

    with pytest.raises(ContactNotFoundError):
        use_case.execute(contact_id="999", account="openclaw@datamaq.com.ar")


def test_create_contact_use_case():
    repo = FakeContactsRepository()
    use_case = CreateContactUseCase(repository=repo)

    dto = CreateContactDTO(
        nombre="Carlos Ruiz",
        email="carlos@empresa.com",
        telefono="+54 11 8888-7777",
        organizacion="Distribuidora Ruiz",
    )
    created = use_case.execute(dto=dto, account="openclaw@datamaq.com.ar")
    assert created.id_contacto == "3"
    assert created.nombre == "Carlos Ruiz"
    assert "BEGIN:VCARD" in created.vcard


def test_update_contact_use_case():
    repo = FakeContactsRepository()
    use_case = UpdateContactUseCase(repository=repo)

    dto = UpdateContactDTO(
        nombre="Agustín Deoz Modificado",
        organizacion="DataMaq Automatización",
    )
    updated = use_case.execute(
        contact_id="1", dto=dto, account="openclaw@datamaq.com.ar"
    )
    assert updated.nombre == "Agustín Deoz Modificado"
    assert updated.organizacion == "DataMaq Automatización"
    assert updated.email == "agustin@datamaq.com.ar"  # Preserved


def test_delete_contact_use_case():
    repo = FakeContactsRepository()
    use_case = DeleteContactUseCase(repository=repo)

    deleted = use_case.execute(contact_id="1", account="openclaw@datamaq.com.ar")
    assert deleted is True

    # Contact is soft deleted
    get_uc = GetContactDetailUseCase(repository=repo)
    with pytest.raises(ContactNotFoundError):
        get_uc.execute(contact_id="1", account="openclaw@datamaq.com.ar")
