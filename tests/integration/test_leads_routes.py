"""Integration tests for leads API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.fastapi.server import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_ingest_lead_endpoint_success(client: TestClient):
    payload = {
        "nombre": "Mariana Gómez",
        "email": "mariana.gomez@autopartes.com",
        "telefono": "+54 9 11 5555-4444",
        "empresa": "Autopartes Tigre S.A.",
        "mensaje": "Consulta por retrofit IoT en centro de mecanizado.",
        "fuente": "landing_telemetria",
        "utm_campaign": "retrofit_iot",
    }

    response = client.post("/api/v1/leads/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "id_contacto" in data
    assert data["id_contacto"] != ""


def test_ingest_lead_endpoint_validation_error(client: TestClient):
    payload = {
        "nombre": "A",  # Min length is 2
        "email": "",
        "telefono": "",
    }

    response = client.post("/api/v1/leads/ingest", json=payload)
    assert response.status_code == 422
