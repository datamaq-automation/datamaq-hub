"""Integration tests para las rutas de /api/v1/tools/."""

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.fastapi.server import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_post_calculadora_cos_fi_success(client: TestClient) -> None:
    """Verifica el endpoint de la calculadora de factor de potencia con envelope APIResponseDTO."""
    payload = {
        "potencia_kw": 50.0,
        "cos_fi_actual": 0.78,
        "factura_base_ars": 850000.0,
        "empresa": "Metalúrgica Garín",
        "tarifa": "T3",
    }
    response = client.post("/api/v1/tools/calculadora-cos-fi", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "data" in data

    resultado = data["data"]
    assert resultado["cos_fi_actual"] == 0.78
    assert resultado["cos_fi_objetivo"] == 0.95
    assert resultado["recargo_porcentaje"] == 21.79
    assert resultado["recargo_mensual_ars"] == 185215.0
    assert resultado["potencia_reactiva_kvar"] > 0
    assert resultado["banco_capacitores_recomendado_kvar"] >= 20.0
    assert "wa.me" in resultado["whatsapp_url"]


def test_post_calculadora_cos_fi_optimo(client: TestClient) -> None:
    """Verifica el cálculo para una instalación sin multas."""
    payload = {
        "potencia_kw": 30.0,
        "cos_fi_actual": 0.97,
        "factura_base_ars": 400000.0,
    }
    response = client.post("/api/v1/tools/calculadora-cos-fi", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["estado"] == "optimo"
    assert data["data"]["recargo_porcentaje"] == 0.0
    assert data["data"]["banco_capacitores_recomendado_kvar"] == 0.0


def test_post_calculadora_cos_fi_validation_error(client: TestClient) -> None:
    """Verifica que inputs inválidos retornen error 422 estandarizado."""
    payload = {
        "potencia_kw": -10.0,
        "cos_fi_actual": 1.5,
    }
    response = client.post("/api/v1/tools/calculadora-cos-fi", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "error" in data
