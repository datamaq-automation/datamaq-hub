"""Unit tests for GmailApiGateway."""

from unittest.mock import patch

import pytest

from src.adapters.gateways.gmail_api_gateway import GmailApiGateway
from src.domain.mail.exceptions import MailAuthenticationError


def test_gmail_api_gateway_missing_credentials():
    gateway = GmailApiGateway(client_id="", client_secret="", refresh_token="")
    with pytest.raises(MailAuthenticationError):
        gateway._get_access_token()


def test_gmail_api_gateway_get_folders_success():
    gateway = GmailApiGateway(
        client_id="cid",
        client_secret="sec",
        refresh_token="ref",
        user_email="docente@abc.gob.ar",
    )

    mock_labels_data = {
        "labels": [
            {"id": "INBOX", "name": "INBOX"},
            {"id": "SENT", "name": "SENT"},
        ]
    }
    mock_inbox_detail = {"messagesTotal": 100, "messagesUnread": 5}
    mock_sent_detail = {"messagesTotal": 20, "messagesUnread": 0}

    with (
        patch.object(gateway, "_get_access_token", return_value="mock_token"),
        patch.object(
            gateway,
            "_make_api_request",
            side_effect=[mock_labels_data, mock_inbox_detail, mock_sent_detail],
        ),
    ):
        folders = gateway.get_folders()

    assert len(folders) == 2
    assert folders[0].nombre == "INBOX"
    assert folders[0].total_mensajes == 100
    assert folders[0].no_leidos == 5


def test_gmail_api_gateway_list_messages_success():
    gateway = GmailApiGateway(
        client_id="cid",
        client_secret="sec",
        refresh_token="ref",
        user_email="docente@abc.gob.ar",
    )

    mock_list_data = {
        "messages": [{"id": "msg101"}],
        "resultSizeEstimate": 1,
    }
    mock_unread_data = {"resultSizeEstimate": 1}
    mock_meta_data = {
        "id": "msg101",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "sad@abc.gob.ar"},
                {"name": "Subject", "value": "Designación Docente"},
                {"name": "Date", "value": "Wed, 28 Aug 2026 12:00:00 -0300"},
            ],
            "parts": [{"filename": "designacion.pdf"}],
        },
    }

    with (
        patch.object(gateway, "_get_access_token", return_value="mock_token"),
        patch.object(
            gateway,
            "_make_api_request",
            side_effect=[mock_list_data, mock_unread_data, mock_meta_data],
        ),
    ):
        messages, total, unread = gateway.list_messages(folder="INBOX", limit=5)

    assert len(messages) == 1
    assert messages[0].uid == "msg101"
    assert messages[0].remitente == "sad@abc.gob.ar"
    assert messages[0].asunto == "Designación Docente"
    assert messages[0].leido is False
    assert messages[0].tiene_adjuntos is True
    assert total == 1
    assert unread == 1


def test_gmail_api_gateway_get_message_by_uid_success():
    gateway = GmailApiGateway(
        client_id="cid",
        client_secret="sec",
        refresh_token="ref",
        user_email="docente@abc.gob.ar",
    )

    mock_full_data = {
        "id": "msg101",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "From", "value": "sad@abc.gob.ar"},
                {"name": "To", "value": "agustinbustos@abc.gob.ar"},
                {"name": "Subject", "value": "Oferta de Horas"},
                {"name": "Date", "value": "Wed, 28 Aug 2026 12:00:00 -0300"},
            ],
            "body": {"size": 0},
            "parts": [
                {
                    "mimeType": "text/plain",
                    "filename": "",
                    "body": {
                        "data": "SG9sYSBBZ3VzdGluLCB0ZSBhZHp1bnRhbW9zIGxhIG9mZXJ0YS4="  # Base64url for text
                    },
                },
                {
                    "mimeType": "application/pdf",
                    "filename": "oferta.pdf",
                    "body": {"size": 1024},
                },
            ],
        },
    }

    with (
        patch.object(gateway, "_get_access_token", return_value="mock_token"),
        patch.object(gateway, "_make_api_request", return_value=mock_full_data),
    ):
        detail = gateway.get_message_by_uid("msg101")

    assert detail is not None
    assert detail.uid == "msg101"
    assert "Hola Agustin" in detail.cuerpo_texto
    assert len(detail.adjuntos) == 1
    assert detail.adjuntos[0].nombre == "oferta.pdf"
