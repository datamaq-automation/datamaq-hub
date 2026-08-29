"""Unit tests for SQLContactsGateway using SQLite memory database."""

import uuid

from src.adapters.gateways.sql_contacts_gateway import SQLContactsGateway
from src.domain.contacts.entities import Contact


def test_sql_contacts_gateway_crud_flow(tmp_path) -> None:
    db_name = f"sqlite:///{tmp_path}/test_contacts_{uuid.uuid4().hex[:8]}.db"
    gateway = SQLContactsGateway(database_url=db_name)
    account = "openclaw@datamaq.com.ar"

    # 1. Create contact
    contact = Contact(
        id_contacto="",
        nombre="Juan Pérez",
        nombre_pila="Juan",
        apellido="Pérez",
        email="juan@perez.com",
        telefono="+54 11 2222-3333",
        organizacion="Pérez Hnos",
        notas="Notas de prueba",
        vcard="",
        modificado="",
        cuenta=account,
    )
    created = gateway.create_contact(contact=contact, account=account)
    assert created.id_contacto != ""
    assert created.nombre == "Juan Pérez"
    cid = created.id_contacto

    # 2. Get by ID
    fetched = gateway.get_contact_by_id(contact_id=cid, account=account)
    assert fetched is not None
    assert fetched.nombre == "Juan Pérez"
    assert fetched.email == "juan@perez.com"

    # 3. List and search
    contacts, total = gateway.list_contacts(account=account, query="Pérez")
    assert total == 1
    assert len(contacts) == 1

    contacts_empty, total_empty = gateway.list_contacts(
        account=account, query="Inexistente"
    )
    assert total_empty == 0
    assert len(contacts_empty) == 0

    # 4. Update
    updated_entity = Contact(
        id_contacto=cid,
        nombre="Juan Pérez Actualizado",
        nombre_pila="Juan",
        apellido="Pérez",
        email="juan_nuevo@perez.com",
        telefono="+54 11 2222-3333",
        organizacion="Pérez Hnos SRL",
        notas="Notas actualizadas",
        vcard="",
        modificado="",
        cuenta=account,
    )
    updated = gateway.update_contact(contact=updated_entity, account=account)
    assert updated.nombre == "Juan Pérez Actualizado"
    assert updated.organizacion == "Pérez Hnos SRL"

    # 5. Delete
    deleted = gateway.delete_contact(contact_id=cid, account=account)
    assert deleted is True

    # 6. Verify soft-delete
    after_del = gateway.get_contact_by_id(contact_id=cid, account=account)
    assert after_del is None
