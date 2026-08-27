"""Unit tests for mail domain entities, value objects, and domain services."""

import pytest

from src.domain.mail.entities import (
    EmailAttachmentMetadata,
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)
from src.domain.mail.exceptions import (
    EmailNotFoundError,
    InvalidEmailAddressError,
    MailAuthenticationError,
    MailboxNotFoundError,
    MailConnectionError,
    MailDomainException,
)
from src.domain.mail.services import MailDecoderService
from src.domain.mail.value_objects import EmailAddress, EmailUID, FolderName


def test_email_address_valid():
    addr = EmailAddress("contacto@datamaq.com.ar")
    assert addr.value == "contacto@datamaq.com.ar"
    assert addr.clean_address == "contacto@datamaq.com.ar"

    addr2 = EmailAddress("Agustín Deoz <agustin.deoz@gmail.com>")
    assert addr2.clean_address == "agustin.deoz@gmail.com"


def test_email_address_invalid():
    with pytest.raises(InvalidEmailAddressError):
        EmailAddress("")

    with pytest.raises(InvalidEmailAddressError):
        EmailAddress("invalid-address-without-at")


def test_email_uid_validation():
    uid = EmailUID("48231")
    assert uid.value == "48231"

    with pytest.raises(ValueError):
        EmailUID("   ")


def test_folder_name_normalization():
    folder = FolderName('"INBOX"')
    assert folder.value == "INBOX"

    folder_empty = FolderName("")
    assert folder_empty.value == "INBOX"


def test_email_entities_immutability():
    att = EmailAttachmentMetadata(
        nombre="documento.pdf",
        content_type="application/pdf",
        tamano_bytes=1024,
    )
    assert att.nombre == "documento.pdf"
    assert att.tamano_bytes == 1024

    folder = EmailFolder(nombre="INBOX", total_mensajes=10, no_leidos=2)
    assert folder.nombre == "INBOX"
    assert folder.total_mensajes == 10
    assert folder.no_leidos == 2

    summary = EmailSummary(
        uid="101",
        remitente="test@example.com",
        destinatarios=["info@datamaq.com.ar"],
        asunto="Prueba",
        fecha="2026-08-27T09:00:00",
        leido=False,
        tiene_adjuntos=True,
    )
    assert summary.uid == "101"
    assert summary.leido is False
    assert summary.tiene_adjuntos is True

    detail = EmailDetail(
        uid="101",
        remitente="test@example.com",
        destinatarios=["info@datamaq.com.ar"],
        cc=[],
        asunto="Prueba",
        fecha="2026-08-27T09:00:00",
        leido=False,
        cuerpo_texto="Contenido",
        cuerpo_html="<p>Contenido</p>",
        adjuntos=[att],
    )
    assert detail.cuerpo_texto == "Contenido"
    assert len(detail.adjuntos) == 1

    unread = UnreadSummary(
        carpeta="INBOX", total_no_leidos=1, ultimos_no_leidos=[summary]
    )
    assert unread.total_no_leidos == 1
    assert len(unread.ultimos_no_leidos) == 1


def test_mail_decoder_service():
    # RFC 2047 Encoded subject
    encoded_subject = "=?utf-8?Q?Consulta_presupuesto_telemetr=C3=ADa?="
    decoded = MailDecoderService.decode_header_str(encoded_subject)
    assert "telemetría" in decoded

    # Empty header
    assert MailDecoderService.decode_header_str(None) == ""

    # Clean email list
    raw_to = "user1@datamaq.com.ar, Agustín <user2@datamaq.com.ar>"
    emails = MailDecoderService.clean_email_list(raw_to)
    assert len(emails) == 2
    assert "user1@datamaq.com.ar" in emails[0]

    # Sanitize text
    dirty_text = "Hola\x00\n\n\n\nMundo  "
    sanitized = MailDecoderService.sanitize_text(dirty_text)
    assert "\x00" not in sanitized
    assert sanitized == "Hola\n\nMundo"


def test_domain_exceptions_properties():
    exc1 = EmailNotFoundError("101", "INBOX")
    assert "101" in exc1.message
    assert exc1.uid == "101"

    exc2 = MailboxNotFoundError("Sent")
    assert "Sent" in exc2.message

    exc3 = MailConnectionError("127.0.0.1", 993, "Timeout")
    assert exc3.port == 993

    exc4 = MailAuthenticationError("user@datamaq.com.ar", "Bad credentials")
    assert exc4.user == "user@datamaq.com.ar"

    exc5 = MailDomainException("Error general")
    assert str(exc5) == "Error general"
