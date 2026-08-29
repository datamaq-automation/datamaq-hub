"""Unit tests for ImapMailGateway parsing and connection handling."""

import imaplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.gateways.imap_mail_gateway import ImapMailGateway
from src.domain.mail.exceptions import (
    MailAuthenticationError,
    MailboxNotFoundError,
    MailConnectionError,
)


def _build_test_multipart_email() -> bytes:
    """Builds a multipart email with plain text, HTML and a PDF attachment."""
    msg = MIMEMultipart("mixed")
    msg["From"] = "cliente@empresa.com"
    msg["To"] = "contacto@datamaq.com.ar"
    msg["Cc"] = "copia@empresa.com"
    msg["Subject"] = "Presupuesto de Sistema"
    msg["Date"] = "Wed, 27 Aug 2026 09:15:00 -0300"

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText("Hola equipo, solicito cotizacion.", "plain", "utf-8"))
    alt.attach(
        MIMEText("<p>Hola equipo, solicito <b>cotizacion</b>.</p>", "html", "utf-8")
    )
    msg.attach(alt)

    pdf_part = MIMEApplication(b"%PDF-1.4 test binary content", "pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename="cotizacion.pdf")
    msg.attach(pdf_part)

    return msg.as_bytes()


def test_imap_gateway_parse_detail():
    gateway = ImapMailGateway()
    raw_email = _build_test_multipart_email()
    fetch_data = [(b"1 (FLAGS (\\Seen) BODY[] {1234}", raw_email)]

    detail = gateway._parse_detail_from_fetch(
        uid="1001", folder="INBOX", fetch_response=fetch_data
    )

    assert detail is not None
    assert detail.uid == "1001"
    assert detail.remitente == "cliente@empresa.com"
    assert detail.destinatarios == ["contacto@datamaq.com.ar"]
    assert detail.cc == ["copia@empresa.com"]
    assert detail.asunto == "Presupuesto de Sistema"
    assert detail.leido is True
    assert "solicito cotizacion" in detail.cuerpo_texto
    assert "<b>cotizacion</b>" in detail.cuerpo_html
    assert len(detail.adjuntos) == 1
    assert detail.adjuntos[0].nombre == "cotizacion.pdf"
    assert detail.adjuntos[0].content_type == "application/pdf"
    assert detail.adjuntos[0].tamano_bytes > 0


def test_imap_gateway_parse_summary():
    gateway = ImapMailGateway()
    raw_headers = (
        b"From: remitente@test.com\r\n"
        b"To: destino@datamaq.com.ar\r\n"
        b"Subject: Test Subject\r\n"
        b"Date: Wed, 27 Aug 2026 10:00:00 -0300\r\n"
        b"Content-Type: multipart/mixed;\r\n\r\n"
    )
    fetch_data = [(b"1 (FLAGS () BODY[HEADER] {200}", raw_headers)]

    summary = gateway._parse_summary_from_fetch(
        uid="50", folder="INBOX", fetch_response=fetch_data
    )

    assert summary is not None
    assert summary.uid == "50"
    assert summary.remitente == "remitente@test.com"
    assert summary.asunto == "Test Subject"
    assert summary.leido is False
    assert summary.tiene_adjuntos is True


def test_imap_gateway_missing_credentials():
    gateway = ImapMailGateway(user="", password="")
    mock_client = MagicMock()

    with (
        patch("imaplib.IMAP4_SSL", return_value=mock_client),
        pytest.raises(MailAuthenticationError) as exc_info,
    ):
        gateway._create_connection()
    assert "no configuradas" in exc_info.value.message


def test_imap_gateway_connection_timeout():
    gateway = ImapMailGateway(
        host="192.0.2.1",
        port=993,
        user="test@datamaq.com.ar",
        password="pwd",
        timeout_seconds=1,
    )

    with (
        patch("imaplib.IMAP4_SSL", side_effect=TimeoutError("Timed out")),
        pytest.raises(MailConnectionError) as exc_info,
    ):
        gateway._create_connection()
    assert "192.0.2.1" in exc_info.value.message
    assert "Timeout" in exc_info.value.message


def test_imap_gateway_auth_error():
    gateway = ImapMailGateway(user="invalid@datamaq.com.ar", password="wrongpassword")
    mock_client = MagicMock()
    mock_client.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    with (
        patch("imaplib.IMAP4_SSL", return_value=mock_client),
        pytest.raises(MailAuthenticationError) as exc_info,
    ):
        gateway._create_connection()
    assert "invalid@datamaq.com.ar" in exc_info.value.message


def test_imap_gateway_list_messages_folder_not_found():
    gateway = ImapMailGateway()
    mock_client = MagicMock()
    mock_client.select.return_value = ("NO", [b"Mailbox does not exist"])

    with (
        patch.object(gateway, "_create_connection", return_value=mock_client),
        pytest.raises(MailboxNotFoundError),
    ):
        gateway.list_messages(folder="CarpetaInexistente")


def test_imap_gateway_get_folders():
    gateway = ImapMailGateway()
    mock_client = MagicMock()
    mock_client.list.return_value = (
        "OK",
        [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasNoChildren \\Sent) "/" "Sent"',
        ],
    )
    mock_client.status.side_effect = [
        ("OK", [b'"INBOX" (MESSAGES 12 UNSEEN 3)']),
        ("OK", [b'"Sent" (MESSAGES 45 UNSEEN 0)']),
    ]

    with patch.object(gateway, "_create_connection", return_value=mock_client):
        folders = gateway.get_folders()

    assert len(folders) == 2
    assert folders[0].nombre == "INBOX"
    assert folders[0].total_mensajes == 12
    assert folders[0].no_leidos == 3
    assert folders[1].nombre == "Sent"
    assert folders[1].total_mensajes == 45
    assert folders[1].no_leidos == 0


def test_imap_gateway_list_messages_success():
    gateway = ImapMailGateway()
    mock_client = MagicMock()
    mock_client.select.return_value = ("OK", [b"12"])
    mock_client.status.return_value = ("OK", [b'"INBOX" (MESSAGES 12 UNSEEN 3)'])
    mock_client.uid.side_effect = [
        ("OK", [b"101 102"]),
        (
            "OK",
            [
                (
                    b"1 (FLAGS (\\Seen) BODY[HEADER.FIELDS ...] {100}",
                    b"From: test@datamaq.com.ar\r\nSubject: Test\r\n\r\n",
                )
            ],
        ),
        (
            "OK",
            [
                (
                    b"2 (FLAGS () BODY[HEADER.FIELDS ...] {100}",
                    b"From: test2@datamaq.com.ar\r\nSubject: Test 2\r\n\r\n",
                )
            ],
        ),
    ]

    with patch.object(gateway, "_create_connection", return_value=mock_client):
        messages, total, unread = gateway.list_messages(folder="INBOX", limit=10)

    assert total == 12
    assert unread == 3
    assert len(messages) == 2
    assert messages[0].uid == "102"  # Newest first


def test_imap_gateway_get_message_by_uid_success():
    gateway = ImapMailGateway()
    raw_email = _build_test_multipart_email()
    mock_client = MagicMock()
    mock_client.select.return_value = ("OK", [b"12"])
    mock_client.uid.return_value = (
        "OK",
        [(b"1 (FLAGS (\\Seen) BODY[] {1234}", raw_email)],
    )

    with patch.object(gateway, "_create_connection", return_value=mock_client):
        detail = gateway.get_message_by_uid("1001", folder="INBOX")

    assert detail is not None
    assert detail.uid == "1001"
    assert detail.asunto == "Presupuesto de Sistema"


def test_imap_gateway_get_unread_summary_success():
    gateway = ImapMailGateway()
    mock_client = MagicMock()
    mock_client.select.return_value = ("OK", [b"12"])
    mock_client.status.return_value = ("OK", [b'"INBOX" (MESSAGES 12 UNSEEN 1)'])
    mock_client.uid.side_effect = [
        ("OK", [b"102"]),
        (
            "OK",
            [
                (
                    b"1 (FLAGS () BODY[HEADER.FIELDS ...] {100}",
                    b"From: test@datamaq.com.ar\r\nSubject: Test\r\n\r\n",
                )
            ],
        ),
    ]

    with patch.object(gateway, "_create_connection", return_value=mock_client):
        summary = gateway.get_unread_summary(folder="INBOX", limit=5)

    assert summary.carpeta == "INBOX"
    assert summary.total_no_leidos == 1
    assert len(summary.ultimos_no_leidos) == 1


def test_imap_gateway_xoauth2_success():
    """Verifica autenticación IMAP mediante XOAUTH2."""
    gateway = ImapMailGateway(
        host="imap.gmail.com",
        port=993,
        user="docente@abc.gob.ar",
        oauth2_client_id="mock_client_id",
        oauth2_client_secret="mock_client_secret",
        oauth2_refresh_token="mock_refresh_token",
    )
    mock_client = MagicMock()

    with (
        patch.object(
            gateway, "_get_oauth2_access_token", return_value="mock_access_token"
        ),
        patch("imaplib.IMAP4_SSL", return_value=mock_client),
    ):
        conn = gateway._create_connection()

    assert conn == mock_client
    mock_client.authenticate.assert_called_once()
    args, _ = mock_client.authenticate.call_args
    assert args[0] == "XOAUTH2"
    auth_cb = args[1]
    assert b"docente@abc.gob.ar" in auth_cb(None)
    assert b"mock_access_token" in auth_cb(None)


def test_imap_gateway_xoauth2_token_exchange_error():
    """Verifica manejo de error al canjear refresh token con Google OAuth2."""
    gateway = ImapMailGateway(
        host="imap.gmail.com",
        port=993,
        user="docente@abc.gob.ar",
        oauth2_client_id="mock_client_id",
        oauth2_client_secret="mock_client_secret",
        oauth2_refresh_token="mock_refresh_token",
    )

    with (
        patch("urllib.request.urlopen", side_effect=Exception("Network failure")),
        pytest.raises(MailAuthenticationError) as exc_info,
    ):
        gateway._get_oauth2_access_token()

    assert "Error conectando al endpoint" in exc_info.value.message
