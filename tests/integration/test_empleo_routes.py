"""Integration tests for /api/v1/empleo/ routes."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.adapters.controllers.dependencies import get_empleo_controller
from src.adapters.controllers.empleo_controller import EmpleoController
from src.adapters.gateways.empleo.sql_oportunidades_gateway import (
    SQLOportunidadesGateway,
)
from src.application.use_cases.empleo.buscar_ofertas_vaca_muerta_use_case import (
    BuscarOfertasVacaMuertaUseCase,
)
from src.application.use_cases.empleo.gestionar_oportunidades_use_cases import (
    ActualizarEstadoOportunidadUseCase,
    ListarInteraccionesUseCase,
    ListarOportunidadesUseCase,
    RegistrarInteraccionUseCase,
    RegistrarOportunidadUseCase,
)
from src.domain.empleo.entities import OfertaLaboral
from src.domain.empleo.value_objects import FuenteOferta, ModalidadTrabajo
from src.infrastructure.fastapi.server import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()

    mock_portal = MagicMock()
    mock_portal.obtener_fuente.return_value = FuenteOferta.YPF
    mock_portal.buscar_ofertas.return_value = [
        OfertaLaboral(
            id_oferta="ypf-101",
            titulo="Ingeniero de Automatización y SCADA",
            empresa="YPF S.A.",
            ubicacion="Añelo, Neuquén",
            descripcion="Supervisión de PLCs, telemetría y SCADA en pozo.",
            url_postulacion="https://jobs.ypf.com/101",
            fuente=FuenteOferta.YPF,
            modalidad=ModalidadTrabajo.ROTACIONAL_YACIMIENTO,
        )
    ]

    mock_use_case = BuscarOfertasVacaMuertaUseCase(portales=[mock_portal])
    repo = SQLOportunidadesGateway("sqlite:///:memory:")
    test_controller = EmpleoController(
        buscar_ofertas_uc=mock_use_case,
        registrar_oportunidad_uc=RegistrarOportunidadUseCase(repository=repo),
        listar_oportunidades_uc=ListarOportunidadesUseCase(repository=repo),
        actualizar_estado_uc=ActualizarEstadoOportunidadUseCase(repository=repo),
        registrar_interaccion_uc=RegistrarInteraccionUseCase(repository=repo),
        listar_interacciones_uc=ListarInteraccionesUseCase(repository=repo),
    )

    app.dependency_overrides[get_empleo_controller] = lambda: test_controller
    return TestClient(app)


def test_get_empleo_vaca_muerta_success(client: TestClient) -> None:
    response = client.get(
        "/api/v1/empleo/vaca-muerta?q=automatizacion&solo_vaca_muerta=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    resultado = data["data"]
    assert resultado["total_encontradas"] == 1
    assert len(resultado["ofertas"]) == 1
    oferta = resultado["ofertas"][0]
    assert oferta["id_oferta"] == "ypf-101"
    assert oferta["empresa"] == "YPF S.A."
    assert oferta["score_afinidad"] >= 40.0


def test_post_empleo_vaca_muerta_con_perfil(client: TestClient) -> None:
    payload = {
        "palabras_clave": ["automatizacion", "scada"],
        "solo_vaca_muerta": True,
        "min_score_afinidad": 50.0,
        "perfil": {
            "titulo_deseado": "Ingeniero de Automatización",
            "palabras_clave_prioritarias": ["SCADA", "PLC"],
            "palabras_clave_secundarias": ["Telemetría"],
            "ubicaciones_preferidas": ["Añelo", "Neuquén"],
            "modalidades_admitidas": ["ROTACIONAL_YACIMIENTO"],
        },
    }
    response = client.post("/api/v1/empleo/vaca-muerta", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["ofertas"]) == 1


def test_crud_oportunidades_y_seguimiento(client: TestClient) -> None:
    # 1. Registrar oportunidad
    post_payload = {
        "titulo": "Ingeniero Eléctrico de Planta",
        "empresa": "Tecpetrol",
        "ubicacion": "Añelo",
        "estado": "DETECTADA",
        "salario_moneda": "ARS",
        "notas": "Detectada en portal corporativo",
    }
    resp = client.post("/api/v1/empleo/oportunidades", json=post_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    op_id = data["data"]["id"]
    assert op_id is not None
    assert data["data"]["titulo"] == "Ingeniero Eléctrico de Planta"
    assert data["data"]["estado"] == "DETECTADA"

    # 2. Listar oportunidades
    resp = client.get("/api/v1/empleo/oportunidades")
    assert resp.status_code == 200
    ops = resp.json()["data"]
    assert len(ops) == 1
    assert ops[0]["empresa"] == "Tecpetrol"

    # 3. Filtrar por empresa
    resp_filtrada = client.get("/api/v1/empleo/oportunidades?empresa=Tecpetrol")
    assert resp_filtrada.status_code == 200
    assert len(resp_filtrada.json()["data"]) == 1

    resp_vacia = client.get("/api/v1/empleo/oportunidades?empresa=Inexistente")
    assert resp_vacia.status_code == 200
    assert len(resp_vacia.json()["data"]) == 0

    # 4. Actualizar estado (PATCH)
    patch_payload = {
        "nuevo_estado": "POSTULADA",
        "notas": "CV enviado a través del portal de Tecpetrol",
    }
    resp = client.patch(
        f"/api/v1/empleo/oportunidades/{op_id}/estado", json=patch_payload
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["estado"] == "POSTULADA"
    assert data["data"]["notas"] == "CV enviado a través del portal de Tecpetrol"

    # 5. Registrar interacción
    interaccion_payload = {
        "fecha": "2026-09-06",
        "canal": "EMAIL",
        "contacto_nombre": "RRHH Tecpetrol",
        "resumen": "Confirmación automática de postulación recibida",
    }
    resp = client.post(
        f"/api/v1/empleo/oportunidades/{op_id}/interacciones",
        json=interaccion_payload,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["oportunidad_id"] == op_id
    assert data["data"]["contacto_nombre"] == "RRHH Tecpetrol"

    # 6. Listar interacciones
    resp = client.get(f"/api/v1/empleo/oportunidades/{op_id}/interacciones")
    assert resp.status_code == 200
    interacciones = resp.json()["data"]
    assert len(interacciones) == 1
    assert interacciones[0]["canal"] == "EMAIL"
