"""Integration tests for FastAPI mail routes."""

import pytest
from fastapi.testclient import TestClient

from src.adapters.controllers.mail_controller import MailController
from src.application.use_cases.get_mail_detail import GetMailDetailUseCase
from src.application.use_cases.get_unread_summary import GetUnreadSummaryUseCase
from src.application.use_cases.list_inbox_messages import ListInboxMessagesUseCase
from src.application.use_cases.list_mail_folders import ListMailFoldersUseCase
from src.infrastructure.fastapi.routes.mail_routes import (
    get_configured_mail_controller,
)
from src.infrastructure.fastapi.server import create_app
from tests.unit.test_mail_use_cases import FakeMailReaderGateway


@pytest.fixture
def mail_client() -> TestClient:
    app = create_app()
    fake_gateway = FakeMailReaderGateway()
    test_controller = MailController(
        list_folders_use_case=ListMailFoldersUseCase(mail_reader=fake_gateway),
        list_inbox_use_case=ListInboxMessagesUseCase(mail_reader=fake_gateway),
        get_mail_detail_use_case=GetMailDetailUseCase(mail_reader=fake_gateway),
        get_unread_summary_use_case=GetUnreadSummaryUseCase(mail_reader=fake_gateway),
    )

    app.dependency_overrides[get_configured_mail_controller] = lambda: test_controller
    client = TestClient(app)
    return client


def test_get_folders_route(mail_client: TestClient):
    response = mail_client.get("/api/v1/mail/carpetas")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2
    assert data["data"][0]["nombre"] == "INBOX"
    assert data["data"][0]["total_mensajes"] == 2
    assert data["data"][0]["no_leidos"] == 1


def test_get_inbox_messages_route(mail_client: TestClient):
    response = mail_client.get("/api/v1/mail/inbox?limit=10&sin_leer=true")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["carpeta"] == "INBOX"
    assert len(data["data"]["correos"]) == 1
    assert data["data"]["correos"][0]["uid"] == "2"
    assert data["data"]["correos"][0]["leido"] is False


def test_get_unread_summary_route(mail_client: TestClient):
    response = mail_client.get("/api/v1/mail/inbox/sin-leer")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_no_leidos"] == 1
    assert len(data["data"]["ultimos_no_leidos"]) == 1


def test_get_message_detail_route_success(mail_client: TestClient):
    response = mail_client.get("/api/v1/mail/inbox/2")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["uid"] == "2"
    assert data["data"]["asunto"] == "Segundo Correo No Leído"
    assert len(data["data"]["adjuntos"]) == 1
    assert data["data"]["adjuntos"][0]["nombre"] == "reporte.pdf"


def test_get_message_detail_shortcut_route(mail_client: TestClient):
    response = mail_client.get("/api/v1/mail/1")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["uid"] == "1"
    assert data["data"]["asunto"] == "Primer Correo"


def test_get_message_detail_not_found(mail_client: TestClient):
    response = mail_client.get("/api/v1/mail/inbox/999")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "EMAIL_NOT_FOUND"
    assert "999" in data["error"]["message"]


def test_get_folders_with_account_query_route(mail_client: TestClient):
    """Verifica que el parámetro account='abc' sea aceptado en /carpetas."""
    response = mail_client.get("/api/v1/mail/carpetas?account=abc")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2


def test_get_unread_summary_with_account_query_route(mail_client: TestClient):
    """Verifica que el parámetro account='datamaq' sea aceptado en /inbox/sin-leer."""
    response = mail_client.get("/api/v1/mail/inbox/sin-leer?account=datamaq&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_no_leidos"] == 1
