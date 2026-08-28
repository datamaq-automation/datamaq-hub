"""Integration tests for FastAPI HTTP controllers."""

import io
from pathlib import Path

from starlette.testclient import TestClient


def test_health_controller(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "datamaq-hub"


def test_root_controller(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/v1/health"


def test_parse_real_pdf_controller(client: TestClient, sample_pdf_path: Path):
    if not sample_pdf_path.exists():
        return

    with open(sample_pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/recibos/parse",
            files={"file": (sample_pdf_path.name, f, "application/pdf")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["tipo_recibo"] == "DGCYE_PBA"
    assert bool(data["agente"]["nombre_completo"])
    assert data["agente"]["numero_documento"] == "36528392"
    assert data["agente"]["cuil"] == "20-36528392-4"
    assert len(data["resumen_liquidos"]) == 14
    assert len(data["liquidaciones"]) == 14
    assert data["totales"]["total_liquido"] == 2585423.32


def test_parse_invalid_extension(client: TestClient):
    fake_txt = io.BytesIO(b"Not a PDF")
    response = client.post(
        "/api/v1/recibos/parse",
        files={"file": ("test.txt", fake_txt, "text/plain")},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert "must be a PDF document" in payload["error"]["message"]


def test_parse_empty_pdf(client: TestClient):
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/v1/recibos/parse",
        files={"file": ("empty.pdf", empty_file, "application/pdf")},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert "empty" in payload["error"]["message"]


def test_parse_corrupt_pdf(client: TestClient):
    corrupt_file = io.BytesIO(b"NOT_A_VALID_PDF_HEADER_123456789")
    response = client.post(
        "/api/v1/recibos/parse",
        files={"file": ("corrupt.pdf", corrupt_file, "application/pdf")},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_PDF_ERROR"
