"""Use case for exporting contacts in standard vCard 3.0 format for WhatsApp Business."""

from src.domain.contacts.ports import ContactsRepositoryPort
from src.domain.contacts.services import VCardFormatterService


class ExportarContactosVCardUseCase:
    """Exports address book contacts to consolidated vCard text representation."""

    def __init__(self, contacts_repo: ContactsRepositoryPort) -> None:
        self._contacts_repo = contacts_repo

    def execute(self, account: str = "") -> str:
        contacts, _ = self._contacts_repo.list_contacts(
            account=account, limit=1000, offset=0
        )
        vcard_blocks: list[str] = []

        for c in contacts:
            if c.vcard and "BEGIN:VCARD" in c.vcard:
                vcard_blocks.append(c.vcard.strip() + "\r\n")
            else:
                vcard_text = VCardFormatterService.generate_vcard(
                    name=c.nombre,
                    firstname=c.nombre_pila,
                    surname=c.apellido,
                    email=c.email,
                    phone=c.telefono,
                    organization=c.organizacion,
                    note=c.notas,
                )
                vcard_blocks.append(vcard_text.strip() + "\r\n")

        return "\r\n".join(vcard_blocks)
