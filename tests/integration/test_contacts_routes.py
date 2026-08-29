"""Integration tests for contacts endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.adapters.controllers.dependencies import get_contacts_controller
from src.infrastructure.fastapi.routes.contacts_routes import (
    get_configured_contacts_controller,
)
from src.infrastructure.fastapi.server import create_app
from tests.unit.test_contacts_use_cases import FakeContactsRepository


@pytest.fixture
def contacts_client() -> TestClient:
    app = create_app()
    fake_repo = FakeContactsRepository()
    controller = get_contacts_controller(repository=fake_repo)

    app.dependency_overrides[get_configured_contacts_controller] = lambda: controller
    return TestClient(app)


def test_list_contacts_route(contacts_client: TestClient):
    response = contacts_client.get("/api/v1/contactos")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 2
    assert len(data["data"]["contactos"]) == 2


def test_get_contact_detail_route(contacts_client: TestClient):
    response = contacts_client.get("/api/v1/contactos/1")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id_contacto"] == "1"
    assert data["data"]["nombre"] == "Agustín Deoz"


def test_create_contact_route(contacts_client: TestClient):
    payload = {
        "nombre": "Esteban Morales",
        "email": "esteban@cliente.com",
        "telefono": "+54 11 4444-5555",
        "organizacion": "Industrias Morales",
    }
    response = contacts_client.post("/api/v1/contactos", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["nombre"] == "Esteban Morales"
    assert data["data"]["email"] == "esteban@cliente.com"


def test_update_contact_route(contacts_client: TestClient):
    payload = {"organizacion": "DataMaq Automation Corp"}
    response = contacts_client.put("/api/v1/contactos/1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["organizacion"] == "DataMaq Automation Corp"


def test_delete_contact_route(contacts_client: TestClient):
    response = contacts_client.delete("/api/v1/contactos/1")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["eliminado"] is True

    # 404 on get
    res_get = contacts_client.get("/api/v1/contactos/1")
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "CONTACT_NOT_FOUND"


def test_list_contacts_route_full_default(contacts_client: TestClient):
    """R-K1: /contactos por defecto retorna claves completas (sin romper consumidores)."""
    response = contacts_client.get("/api/v1/contactos")
    assert response.status_code == 200
    data = response.json()
    item = data["data"]["contactos"][0]
    assert set(item.keys()) == {
        "id_contacto",
        "nombre",
        "nombre_pila",
        "apellido",
        "email",
        "telefono",
        "organizacion",
        "notas",
        "vcard",
        "modificado",
        "cuenta",
        "grupos",
    }


def test_list_contacts_route_compact(contacts_client: TestClient):
    """R-K2: compact=true retorna claves reducidas de contacto."""
    response = contacts_client.get("/api/v1/contactos?compact=true")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 2
    item = data["data"]["contactos"][0]
    assert set(item.keys()) == {
        "id_contacto",
        "nombre",
        "email",
        "telefono",
        "organizacion",
    }
