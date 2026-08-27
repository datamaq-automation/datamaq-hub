"""Integration tests for horarios_docencia endpoints."""

from starlette.testclient import TestClient


def test_validar_horarios_docencia_endpoint(client: TestClient) -> None:
    """Verifica el endpoint POST /api/v1/horarios-docencia/validar."""
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


def test_validar_horarios_docencia_formato_invalido(client: TestClient) -> None:
    """Verifica respuesta 422 cuando el formato horario es inválido."""
    payload = {
        "docente_nombre": "Docente Error",
        "cargos": [
            {
                "id_cargo": "C-01",
                "establecimiento": "EEST 1",
                "distrito": "Pilar",
                "cargo_asignatura": "Materia",
                "horarios": [
                    {
                        "dia": "LUNES",
                        "hora_inicio": "25:99",
                        "hora_fin": "09:30",
                    }
                ],
            }
        ],
    }

    response = client.post("/api/v1/horarios-docencia/validar", json=payload)
    assert response.status_code == 422
