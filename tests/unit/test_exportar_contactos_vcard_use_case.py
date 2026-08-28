"""Unit tests for ExportarContactosVCardUseCase."""

from unittest.mock import MagicMock

from src.application.use_cases.exportar_contactos_vcard import (
    ExportarContactosVCardUseCase,
)
from src.domain.contacts.entities import Contact


def test_exportar_contactos_vcard():
    contacts_repo = MagicMock()
    contacts_repo.list_contacts.return_value = (
        [
            Contact(
                id_contacto="1",
                nombre="Agustín DataMaq",
                email="contacto@datamaq.com.ar",
                telefono="+5491111112222",
                organizacion="DataMaq",
                notas="Soporte técnico",
            ),
            Contact(
                id_contacto="2",
                nombre="Cliente Industrial",
                email="planta@industria.com.ar",
                telefono="+5491133334444",
                organizacion="Fábrica Pilar",
            ),
        ],
        2,
    )

    use_case = ExportarContactosVCardUseCase(contacts_repo=contacts_repo)
    vcard_output = use_case.execute(account="agustin.datamaq@gmail.com")

    assert "BEGIN:VCARD" in vcard_output
    assert "FN:Agustín DataMaq" in vcard_output
    assert "TEL;TYPE=CELL:+5491111112222" in vcard_output
    assert "FN:Cliente Industrial" in vcard_output
    assert "END:VCARD" in vcard_output
