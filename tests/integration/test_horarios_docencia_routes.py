"""Integration tests for horarios_docencia endpoints."""

import uuid

from starlette.testclient import TestClient


def test_validar_horarios_docencia_endpoint(client: TestClient) -> None:
    """Verifica el endpoint POST /api/v1/horarios-docencia/validar (ad-hoc)."""
    payload = {
        "docente_nombre": "Agustín Deoz",
        "cuit": "20-36528392-4",
        "dni": "36528392",
        "margen_traslado_minutos": 20,
        "cargos": [
            {
                "id_cargo": "C-01",
                "establecimiento": "EEST N° 1 Pilar",
                "distrito": "Pilar",
                "cargo_asignatura": "Electrotecnia 4to",
                "revista": "TITULAR",
                "ige": "IGE-12345",
                "modulos": 4,
                "es_cargo_base": False,
                "horarios": [
                    {
                        "dia": "LUNES",
                        "hora_inicio": "07:30",
                        "hora_fin": "09:30",
                        "turno": "MANANA",
                    }
                ],
            },
            {
                "id_cargo": "C-02",
                "establecimiento": "EEST N° 1 Pilar",
                "distrito": "Pilar",
                "cargo_asignatura": "Instalaciones 5to",
                "revista": "PROVISIONAL",
                "ige": "IGE-67890",
                "modulos": 4,
                "es_cargo_base": False,
                "horarios": [
                    {
                        "dia": "LUNES",
                        "hora_inicio": "09:45",
                        "hora_fin": "11:45",
                        "turno": "MANANA",
                    }
                ],
            },
        ],
    }

    response = client.post("/api/v1/horarios-docencia/validar", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["es_compatible"] is True
    assert data["data"]["total_cargos"] == 2
    assert data["data"]["total_modulos"] == 8
    assert data["data"]["cantidad_conflictos"] == 0
    assert "LUNES" in data["data"]["grilla_semanal"]
    assert len(data["data"]["grilla_semanal"]["LUNES"]) == 2
    assert data["data"]["grilla_semanal"]["LUNES"][0]["ige"] == "IGE-12345"


def test_flujo_persistencia_temporal_endpoints(client: TestClient) -> None:
    """Verifica el flujo completo REST: alta de designaciones, consulta por fecha, cese e historial."""
    cuit = f"20-{uuid.uuid4().hex[:8]}-4"

    # 1. Alta de designación titular
    payload_titular = {
        "docente_cuit": cuit,
        "ige": "IGE-TIT-01",
        "establecimiento": "EEST N° 1 Pilar",
        "distrito": "Pilar",
        "cargo_asignatura": "Electrotecnia",
        "revista": "TITULAR",
        "modulos": 4,
        "fecha_desde": "2026-03-01",
        "horarios": [
            {
                "dia": "LUNES",
                "hora_inicio": "07:30",
                "hora_fin": "09:30",
                "turno": "MANANA",
            }
        ],
    }
    resp_tit = client.post(
        "/api/v1/horarios-docencia/designaciones", json=payload_titular
    )
    assert resp_tit.status_code == 200
    data_tit = resp_tit.json()["data"]
    id_tit = data_tit["id_designacion"]
    assert data_tit["ige"] == "IGE-TIT-01"

    # 2. Alta de suplencia
    payload_suplente = {
        "docente_cuit": cuit,
        "ige": "IGE-SUP-01",
        "establecimiento": "ISFT N° 199 Tigre",
        "distrito": "Tigre",
        "cargo_asignatura": "Automatización",
        "revista": "SUPLENTE",
        "modulos": 4,
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-06-30",
        "horarios": [
            {
                "dia": "MIERCOLES",
                "hora_inicio": "18:00",
                "hora_fin": "20:00",
                "turno": "VESPERTINO",
            }
        ],
    }
    resp_sup = client.post(
        "/api/v1/horarios-docencia/designaciones", json=payload_suplente
    )
    assert resp_sup.status_code == 200

    # 3. Consultar vigentes en Mayo (2 cargos)
    resp_mayo = client.get(
        f"/api/v1/horarios-docencia/docentes/{cuit}/vigentes?fecha=2026-05-15"
    )
    assert resp_mayo.status_code == 200
    assert resp_mayo.json()["data"]["total_cargos"] == 2

    # 4. Consultar vigentes en Julio (1 cargo)
    resp_julio = client.get(
        f"/api/v1/horarios-docencia/docentes/{cuit}/vigentes?fecha=2026-07-15"
    )
    assert resp_julio.status_code == 200
    assert resp_julio.json()["data"]["total_cargos"] == 1

    # 5. Cesar el titular
    resp_cesar = client.post(
        f"/api/v1/horarios-docencia/designaciones/{id_tit}/cesar",
        json={"fecha_hasta": "2026-08-31", "motivo_cese": "RENUNCIA"},
    )
    assert resp_cesar.status_code == 200
    assert resp_cesar.json()["data"]["motivo_cese"] == "RENUNCIA"

    # 6. Consultar historial completo
    resp_hist = client.get(f"/api/v1/horarios-docencia/docentes/{cuit}/historial")
    assert resp_hist.status_code == 200
    assert len(resp_hist.json()["data"]) == 2
