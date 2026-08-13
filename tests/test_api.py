"""Integration tests for FastAPI REST API endpoints."""

import io
from pathlib import Path

from starlette.testclient import TestClient


def test_health_check_endpoint(client: TestClient):
    """Test health check route."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "service" in data


def test_root_endpoint(client: TestClient):
    """Test root redirect/info endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/v1/health"


def test_parse_real_pdf_endpoint(client: TestClient, sample_pdf_path: Path):
    """Test POST /api/v1/recibos/parse with actual sample PDF."""
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

    # Verify key properties in returned JSON
    assert data["tipo_recibo"] == "DGCYE_PBA"
    assert data["agente"]["nombre_completo"] == "BUSTOS AGUSTÍN"
    assert data["agente"]["numero_documento"] == "36528392"
    assert data["agente"]["cuil"] == "20-36528392-4"
    assert len(data["resumen_liquidos"]) == 14
    assert len(data["liquidaciones"]) == 14
    assert data["totales"]["total_liquido"] == 2585423.32


def test_parse_invalid_file_extension(client: TestClient):
    """Test uploading non-pdf file rejected with 400 Bad Request."""
    fake_txt = io.BytesIO(b"Hello world, not a PDF")
    response = client.post(
        "/api/v1/recibos/parse",
        files={"file": ("document.txt", fake_txt, "text/plain")},
    )
    assert response.status_code == 400
    assert "must be a PDF document" in response.json()["detail"]


def test_parse_empty_pdf(client: TestClient):
    """Test uploading empty PDF file rejected with 400."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/v1/recibos/parse",
        files={"file": ("empty.pdf", empty_file, "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_parse_corrupt_pdf(client: TestClient):
    """Test uploading corrupt PDF with bad signature."""
    corrupt_file = io.BytesIO(b"NOT_A_VALID_PDF_HEADER_123456789")
    response = client.post(
        "/api/v1/recibos/parse",
        files={"file": ("corrupt.pdf", corrupt_file, "application/pdf")},
    )
    assert response.status_code == 400
    assert "magic signature" in response.json()["detail"]
