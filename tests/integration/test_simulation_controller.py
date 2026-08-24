"""Integration tests for salary simulation controller."""

from starlette.testclient import TestClient


def test_simulation_controller_success(client: TestClient):
    payload = {
        "anios_antiguedad": 4,
        "periodo_proyectado": "202608",
        "tope_bonificaciones_modulos": 30.0,
        "designaciones": [
            {
                "secuencia": "016",
                "escuela_codigo": "IS-0199",
                "escuela_nombre": "ISFDyT 199",
                "cargo_nivel": "SM",
                "carga_horaria": 7.0,
                "situacion_revista": "PROV.",
                "dias_trabajados": 30.0,
                "inasistencias_paro": 0.0,
                "aplica_suteba": True,
            },
            {
                "secuencia": "021",
                "escuela_codigo": "IS-0199",
                "escuela_nombre": "ISFDyT 199",
                "cargo_nivel": "SM",
                "carga_horaria": 4.0,
                "situacion_revista": "SUP.",
                "dias_trabajados": 30.0,
            },
            {
                "secuencia": "023",
                "escuela_codigo": "MT-0001",
                "escuela_nombre": "EEST 1 Escobar",
                "cargo_nivel": "PM",
                "carga_horaria": 4.0,
                "situacion_revista": "SUP.",
                "dias_trabajados": 9.0,
                "es_retroactivo": True,
            },
        ],
    }

    response = client.post("/api/v1/simulacion", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True

    data = res_json["data"]
    assert data["periodo_proyectado"] == "202608"
    assert data["anios_antiguedad"] == 4
    assert len(data["cargos_liquidados"]) == 3
    assert data["total_liquido"] > 0
    assert data["total_liquido_regular"] > 0
    assert data["total_liquido_retroactivos"] > 0


def test_simulation_controller_validation_error(client: TestClient):
    # Missing required fields or negative carga_horaria
    payload = {
        "anios_antiguedad": 4,
        "designaciones": [
            {
                "secuencia": "016",
                "escuela_codigo": "IS-0199",
                "escuela_nombre": "ISFDyT 199",
                "cargo_nivel": "SM",
                "carga_horaria": -2.0,  # Invalid <= 0
                "situacion_revista": "PROV.",
            }
        ],
    }

    response = client.post("/api/v1/simulacion", json=payload)
    assert response.status_code == 422


def test_simulation_controller_invalid_period_format(client: TestClient):
    payload = {
        "anios_antiguedad": 4,
        "periodo_proyectado": "202613",  # Month 13 is invalid YYYYMM
        "designaciones": [
            {
                "secuencia": "016",
                "escuela_codigo": "IS-0199",
                "escuela_nombre": "ISFDyT 199",
                "cargo_nivel": "SM",
                "carga_horaria": 7.0,
                "situacion_revista": "PROV.",
            }
        ],
    }

    response = client.post("/api/v1/simulacion", json=payload)
    assert response.status_code == 422
