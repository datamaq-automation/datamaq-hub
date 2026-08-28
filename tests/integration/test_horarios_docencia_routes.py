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
                "modulos": 2,
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
                "modulos": 2,
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
    assert data["data"]["total_modulos"] == 4
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
        "modulos": 2,
        "fecha_desde": "2026-03-01",
        "observaciones": "Designación inicial",
        "cupof": "CUP-01",
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
    data_tit = resp_tit.json()["data"]["designacion"]
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
        "modulos": 2,
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
    id_sup = resp_sup.json()["data"]["designacion"]["id_designacion"]

    # 3. GET /designaciones (Listar con filtros)
    resp_list = client.get(f"/api/v1/horarios-docencia/designaciones?cuit={cuit}")
    assert resp_list.status_code == 200
    assert len(resp_list.json()["data"]) == 2

    # 4. GET /designaciones/{id} (Ficha detallada)
    resp_get = client.get(f"/api/v1/horarios-docencia/designaciones/{id_tit}")
    assert resp_get.status_code == 200
    assert resp_get.json()["data"]["id_designacion"] == id_tit

    # 5. PUT /designaciones/{id} (Actualización)
    resp_put = client.put(
        f"/api/v1/horarios-docencia/designaciones/{id_tit}",
        json={"observaciones": "Modificado vía PUT"},
    )
    assert resp_put.status_code == 200
    assert resp_put.json()["data"]["observaciones"] == "Modificado vía PUT"

    # 6. Consultar vigentes en Mayo (2 cargos)
    resp_mayo = client.get(
        f"/api/v1/horarios-docencia/docentes/{cuit}/vigentes?fecha=2026-05-15"
    )
    assert resp_mayo.status_code == 200
    assert resp_mayo.json()["data"]["total_cargos"] == 2

    # 7. Consultar vigentes en Julio (1 cargo)
    resp_julio = client.get(
        f"/api/v1/horarios-docencia/docentes/{cuit}/vigentes?fecha=2026-07-15"
    )
    assert resp_julio.status_code == 200
    assert resp_julio.json()["data"]["total_cargos"] == 1

    # 8. Cesar el titular
    resp_cesar = client.post(
        f"/api/v1/horarios-docencia/designaciones/{id_tit}/cesar",
        json={"fecha_hasta": "2026-08-31", "motivo_cese": "RENUNCIA"},
    )
    assert resp_cesar.status_code == 200
    assert resp_cesar.json()["data"]["motivo_cese"] == "RENUNCIA"

    # 9. Consultar historial completo
    resp_hist = client.get(f"/api/v1/horarios-docencia/docentes/{cuit}/historial")
    assert resp_hist.status_code == 200
    assert len(resp_hist.json()["data"]) == 2

    # 10. DELETE /designaciones/{id} (Borrado físico de suplencia)
    resp_del = client.delete(f"/api/v1/horarios-docencia/designaciones/{id_sup}")
    assert resp_del.status_code == 200
    assert resp_del.json()["data"]["eliminado"] is True


def test_rechazo_designacion_superpuesta_sin_forzar_endpoint(
    client: TestClient,
) -> None:
    """Verifica que POST /designaciones responde HTTP 409 si hay superposición horaria crítica sin forzar=True."""
    cuit = f"20-{uuid.uuid4().hex[:8]}-4"

    # 1. Crear primer cargo
    payload_1 = {
        "docente_cuit": cuit,
        "ige": "IGE-A",
        "establecimiento": "EEST 1 Pilar",
        "cargo_asignatura": "Química",
        "fecha_desde": "2026-03-01",
        "horarios": [
            {
                "dia": "LUNES",
                "hora_inicio": "14:00",
                "hora_fin": "16:00",
                "turno": "TARDE",
            }
        ],
    }
    r1 = client.post("/api/v1/horarios-docencia/designaciones", json=payload_1)
    assert r1.status_code == 200

    # 2. Intentar crear segundo cargo en el mismo horario sin forzar -> 409 Conflict
    payload_superpuesto = {
        "docente_cuit": cuit,
        "ige": "IGE-B",
        "establecimiento": "ISFT 199 Tigre",
        "cargo_asignatura": "Biología",
        "fecha_desde": "2026-03-01",
        "forzar": False,
        "horarios": [
            {
                "dia": "LUNES",
                "hora_inicio": "15:00",
                "hora_fin": "17:00",
                "turno": "TARDE",
            }
        ],
    }
    r2 = client.post(
        "/api/v1/horarios-docencia/designaciones", json=payload_superpuesto
    )
    assert r2.status_code == 409
    err = r2.json()
    assert err["success"] is False
    assert err["error"]["code"] == "INCOMPATIBILIDAD_HORARIA_CRITICA"

    # 3. Reintentar con forzar=True -> 200 OK
    payload_superpuesto["forzar"] = True
    r3 = client.post(
        "/api/v1/horarios-docencia/designaciones", json=payload_superpuesto
    )
    assert r3.status_code == 200
    assert r3.json()["data"]["es_compatible"] is False
