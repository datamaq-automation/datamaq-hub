"""Integration tests for contacts vCard export endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.fastapi.server import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_export_vcard_endpoint(client: TestClient):
    # First create a test contact
    new_contact = {
        "nombre": "Test VCard Export Contact",
        "email": "test.vcard@datamaq.com.ar",
        "telefono": "+5491199998888",
        "organizacion": "Test Org",
        "notas": "Nota de prueba vCard",
    }
    client.post("/api/v1/contactos", json=new_contact)

    response = client.get("/api/v1/contactos/export/vcard")
    assert response.status_code == 200
    assert "text/vcard" in response.headers.get("content-type", "")
    assert "contactos_datamaq.vcf" in response.headers.get("content-disposition", "")
    content_str = response.text
    assert "BEGIN:VCARD" in content_str
    assert "Test VCard Export Contact" in content_str
