"""Tests de integración para los endpoints de perfil de LinkedIn en empleo_routes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.fastapi.server import create_app

SAMPLE_PDF_PATH = Path("/home/agustin/Descargas/Profile.pdf")


@pytest.fixture
def client() -> TestClient:
    """Cliente de pruebas de FastAPI con todas las dependencias reales."""
    app = create_app()
    return TestClient(app)


def test_cargar_perfil_pdf_multipart_corrupto_retorna_422(client: TestClient) -> None:
    """Valida que subir bytes no correspondientes a un PDF válido retorna 422 de dominio."""
    response = client.post(
        "/api/v1/empleo/perfil/cargar-pdf",
        files={
            "file": (
                "invalido.pdf",
                b"esto no es un archivo pdf valido",
                "application/pdf",
            )
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "LINKEDIN_PDF_PARSING_ERROR"


def test_procesar_pdf_local_inexistente_retorna_422(client: TestClient) -> None:
    """Valida que indicar un archivo inexistente en el host retorna 422 de dominio."""
    response = client.post(
        "/api/v1/empleo/perfil/procesar-pdf-local",
        json={
            "pdf_path": "/tmp/archivo_inexistente_totalmente_12345.pdf",
            "guardar_como_yaml": False,
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "LINKEDIN_PDF_PARSING_ERROR"


@pytest.mark.skipif(
    not SAMPLE_PDF_PATH.exists(),
    reason="Requiere el archivo local /home/agustin/Descargas/Profile.pdf",
)
def test_cargar_perfil_pdf_multipart_real(client: TestClient) -> None:
    """Prueba la subida de un PDF real de LinkedIn mediante multipart/form-data."""
    pdf_bytes = SAMPLE_PDF_PATH.read_bytes()
    response = client.post(
        "/api/v1/empleo/perfil/cargar-pdf",
        files={"file": ("Profile.pdf", pdf_bytes, "application/pdf")},
        params={"guardar_como_yaml": False},
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    perfil = res["data"]
    assert "Agustin Bustos" in perfil["contacto"]["nombre"]
    assert "Industria 4.0" in perfil["titular"] or "Tecnología" in perfil["titular"]
    assert len(perfil["experiencias"]) >= 3
    assert len(perfil["palabras_clave_detectadas"]) >= 5


@pytest.mark.skipif(
    not SAMPLE_PDF_PATH.exists(),
    reason="Requiere el archivo local /home/agustin/Descargas/Profile.pdf",
)
def test_procesar_pdf_local_real_y_persistencia_yaml(client: TestClient) -> None:
    """Prueba el endpoint local con persistencia opcional a YAML."""
    response = client.post(
        "/api/v1/empleo/perfil/procesar-pdf-local",
        json={"pdf_path": str(SAMPLE_PDF_PATH), "guardar_como_yaml": True},
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    perfil = res["data"]
    assert perfil["contacto"]["nombre"] == "Agustin Bustos"

    # Verificar que se generó el YAML en data/perfiles/Profile.yaml
    yaml_path = Path("data/perfiles/Profile.yaml")
    try:
        assert yaml_path.exists()
        contenido_yaml = yaml_path.read_text(encoding="utf-8")
        assert "contacto:" in contenido_yaml
        assert "Agustin Bustos" in contenido_yaml
    finally:
        yaml_path.unlink(missing_ok=True)
