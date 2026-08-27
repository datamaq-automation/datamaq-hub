"""Unit tests for contacts domain entities, value objects, and domain services."""

import pytest

from src.domain.contacts.entities import Contact
from src.domain.contacts.exceptions import (
    ContactNotFoundError,
    ContactsDomainException,
    InvalidContactDataError,
)
from src.domain.contacts.services import VCardFormatterService
from src.domain.contacts.value_objects import ContactId, EmailAddress, PhoneNumber


def test_contact_id_validation():
    cid = ContactId("105")
    assert cid.value == "105"

    with pytest.raises(InvalidContactDataError):
        ContactId("")

    with pytest.raises(InvalidContactDataError):
        ContactId("   ")


def test_email_address_validation():
    email = EmailAddress("contacto@datamaq.com.ar")
    assert email.value == "contacto@datamaq.com.ar"

    with pytest.raises(InvalidContactDataError):
        EmailAddress("invalid-email-format")

    with pytest.raises(InvalidContactDataError):
        EmailAddress("")


def test_phone_number_sanitization():
    phone = PhoneNumber("+54 (11) 4444-5555 ext. 123")
    assert "+54" in phone.value
    assert "4444-5555" in phone.value


def test_contact_entity_immutability():
    contact = Contact(
        id_contacto="1",
        nombre="Agustín Deoz",
        nombre_pila="Agustín",
        apellido="Deoz",
        email="agustin@datamaq.com.ar",
        telefono="+54 11 1234-5678",
        organizacion="DataMaq",
        notas="Fundador",
        vcard="",
        modificado="2026-08-27T10:00:00",
        eliminado=False,
        cuenta="openclaw@datamaq.com.ar",
        grupos=["Equipo", "Directorio"],
    )
    assert contact.nombre == "Agustín Deoz"
    assert len(contact.grupos) == 2
    assert contact.eliminado is False


def test_vcard_formatter_generate_and_parse():
    vcard = VCardFormatterService.generate_vcard(
        name="Martín Gómez",
        firstname="Martín",
        surname="Gómez",
        email="martin@empresa.com",
        phone="+54 11 9999-8888",
        organization="Tech S.A.",
        note="Cliente VIP",
    )
    assert "BEGIN:VCARD" in vcard
    assert "FN:Martín Gómez" in vcard
    assert "EMAIL;TYPE=INTERNET:martin@empresa.com" in vcard
    assert "END:VCARD" in vcard

    parsed = VCardFormatterService.parse_vcard_fields(vcard)
    assert parsed["name"] == "Martín Gómez"
    assert parsed["firstname"] == "Martín"
    assert parsed["surname"] == "Gómez"
    assert parsed["email"] == "martin@empresa.com"
    assert parsed["phone"] == "+54 11 9999-8888"
    assert parsed["organization"] == "Tech S.A."
    assert parsed["note"] == "Cliente VIP"


def test_contacts_exceptions():
    exc = ContactNotFoundError("999", "admin@datamaq.com.ar")
    assert "999" in exc.message
    assert exc.contact_id == "999"

    exc2 = ContactsDomainException("Error general")
    assert str(exc2) == "Error general"
