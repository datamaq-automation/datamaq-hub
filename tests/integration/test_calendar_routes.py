"""Integration tests for calendar endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.adapters.controllers.dependencies import get_calendar_controller
from src.infrastructure.fastapi.routes.calendar_routes import (
    get_configured_calendar_controller,
)
from src.infrastructure.fastapi.server import create_app
from tests.unit.test_calendar_use_cases import FakeCalendarRepository


@pytest.fixture
def calendar_client() -> TestClient:
    app = create_app()
    fake_repo = FakeCalendarRepository()
    controller = get_calendar_controller(repository=fake_repo)

    app.dependency_overrides[get_configured_calendar_controller] = lambda: controller
    return TestClient(app)


def test_list_events_route(calendar_client: TestClient):
    response = calendar_client.get("/api/v1/calendario/eventos")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["titulo"] == "Reunión de Planificación"


def test_get_upcoming_events_route(calendar_client: TestClient):
    response = calendar_client.get("/api/v1/calendario/proximos?dias=30")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_check_availability_route(calendar_client: TestClient):
    response = calendar_client.get(
        "/api/v1/calendario/disponibilidad?fecha=2026-08-28&duracion_minutos=30"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["fecha"] == "2026-08-28"
    assert len(data["data"]["bloques"]) > 0


def test_create_event_route(calendar_client: TestClient):
    payload = {
        "titulo": "Reunión Comercial",
        "inicio": "2026-08-28T16:00:00",
        "fin": "2026-08-28T17:00:00",
        "ubicacion": "Meet",
        "descripcion": "Demostración de telemetría",
        "asistentes": ["agustin@datamaq.com.ar", "cliente@empresa.com"],
    }
    response = calendar_client.post("/api/v1/calendario/eventos", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["titulo"] == "Reunión Comercial"
    assert data["data"]["id_evento"] == "2"


def test_update_event_route(calendar_client: TestClient):
    payload = {"ubicacion": "Oficina Central y Meet"}
    response = calendar_client.put("/api/v1/calendario/eventos/1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["ubicacion"] == "Oficina Central y Meet"


def test_delete_event_route(calendar_client: TestClient):
    response = calendar_client.delete("/api/v1/calendario/eventos/1")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["eliminado"] is True

    # 404 on get
    res_get = calendar_client.get("/api/v1/calendario/eventos/1")
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "EVENT_NOT_FOUND"
