"""Integration tests for docencia calendar synchronization routes."""

import pytest
from fastapi.testclient import TestClient

from src.adapters.controllers.dependencies import get_calendar_controller
from src.infrastructure.fastapi.routes.calendar_routes import (
    get_configured_calendar_controller,
)
from src.infrastructure.fastapi.server import create_app
from tests.unit.test_calendar_use_cases import FakeCalendarRepository
from tests.unit.test_sincronizar_agenda_docente_use_case import (
    FakeDesignacionRepository,
)


@pytest.fixture
def calendar_docencia_client() -> TestClient:
    app = create_app()
    fake_cal_repo = FakeCalendarRepository()
    fake_doc_repo = FakeDesignacionRepository()

    controller = get_calendar_controller(
        repository=fake_cal_repo, designacion_repository=fake_doc_repo
    )

    app.dependency_overrides[get_configured_calendar_controller] = lambda: controller
    return TestClient(app)


def test_sincronizar_docencia_route(calendar_docencia_client: TestClient):
    payload = {
        "cuit": "20365283921",
        "fecha_desde": "2026-09-01",
        "fecha_hasta": "2026-09-07",
        "limpiar_previos": True,
    }
    response = calendar_docencia_client.post(
        "/api/v1/calendario/docencia/sincronizar", json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["cuit"] == "20365283921"
    assert data["data"]["total_eventos_creados"] == 2


def test_consultar_agenda_docente_route(calendar_docencia_client: TestClient):
    # First sync
    calendar_docencia_client.post(
        "/api/v1/calendario/docencia/sincronizar",
        json={
            "cuit": "20365283921",
            "fecha_desde": "2026-09-01",
            "fecha_hasta": "2026-09-07",
        },
    )

    # Then query
    response = calendar_docencia_client.get(
        "/api/v1/calendario/docencia/agenda?fecha_desde=2026-09-01&fecha_hasta=2026-09-07&solo_docencia=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2
    assert "Electrónica Aplicada" in data["data"][0]["titulo"]
