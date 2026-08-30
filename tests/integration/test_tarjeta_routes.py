"""Pruebas de integración para la ruta de carga de resúmenes de tarjeta."""

from collections.abc import Generator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.adapters.controllers.dependencies import get_tarjeta_controller
from src.adapters.controllers.tarjeta_controller import TarjetaController
from src.adapters.gateways.pdf_tarjeta_parser_gateway import PDFTarjetaParserGateway
from src.adapters.gateways.sql_tarjeta_gateway import SQLTarjetaGateway
from src.application.use_cases.procesar_resumen_tarjeta import (
    ProcesarResumenTarjetaUseCase,
)
from src.main import app

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "tarjeta_credito"


def _build_controller() -> TarjetaController:
    return TarjetaController(
        procesar_use_case=ProcesarResumenTarjetaUseCase(
            parser=PDFTarjetaParserGateway(),
            repository=SQLTarjetaGateway("sqlite:///:memory:"),
        )
    )


@pytest.fixture
def tarjeta_client() -> Generator[TestClient, None, None]:
    """TestClient con el gateway de tarjetas en memoria aislada."""
    app.dependency_overrides[get_tarjeta_controller] = _build_controller
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_cargar_resumen_bbva_visa(tarjeta_client: TestClient) -> None:
    ruta = DATA_DIR / "20260829_visa.pdf"
    if not ruta.exists():
        pytest.skip(f"PDF de tarjeta no encontrado: {ruta}")
    with ruta.open("rb") as archivo:
        response = tarjeta_client.post(
            "/api/v1/tarjetas/cargar",
            files={"file": ("visa.pdf", archivo, "application/pdf")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    resumen = body["data"]
    assert resumen["banco"] == "BBVA"
    assert resumen["tarjeta_tipo"] == "VISA"
    assert resumen["numero_cuenta"] == "1097452662"
    assert resumen["saldo_pesos"] == 144565.27
    assert len(resumen["consumos"]) == 3


def test_cargar_resumen_bapro_visa(tarjeta_client: TestClient) -> None:
    ruta = DATA_DIR / "1151377322.01.27-08-26.pdf"
    if not ruta.exists():
        pytest.skip(f"PDF de tarjeta no encontrado: {ruta}")
    with ruta.open("rb") as archivo:
        response = tarjeta_client.post(
            "/api/v1/tarjetas/cargar",
            files={"file": ("bapro.pdf", archivo, "application/pdf")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    resumen = body["data"]
    assert resumen["banco"] == "BAPRO"
    assert resumen["tarjeta_tipo"] == "VISA"
    assert resumen["numero_cuenta"] == "1151377322"
    assert resumen["saldo_dolares"] == 55.78
    assert resumen["consumos"] == []


def test_cargar_resumen_pdf_invalido(tarjeta_client: TestClient) -> None:
    response = tarjeta_client.post(
        "/api/v1/tarjetas/cargar",
        files={"file": ("invalido.pdf", b"no-es-un-pdf", "application/pdf")},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "TARJETA_PARSING_ERROR"
