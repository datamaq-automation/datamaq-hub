"""Pruebas de integración para las rutas de agenda /api/v1/agenda/briefing."""

from starlette.testclient import TestClient


def test_endpoint_briefing_diario(client: TestClient) -> None:
    # 1. Crear una tarea para el docente
    payload_tarea = {
        "titulo": "Preparar parcial de Bases de Datos",
        "prioridad": "ALTA",
        "categoria": "DOCENCIA",
        "docente_cuit": "20-36528392-4",
    }
    resp_t = client.post("/api/v1/tareas", json=payload_tarea)
    assert resp_t.status_code == 201
    id_tarea = resp_t.json()["data"]["id_tarea"]

    # 2. Consultar el briefing diario
    resp_b = client.get("/api/v1/agenda/briefing?cuit=20365283924&fecha=2026-08-28")
    assert resp_b.status_code == 200
    data = resp_b.json()
    assert data["success"] is True
    briefing = data["data"]

    assert briefing["docente_cuit"] == "20365283924"
    assert briefing["fecha"] == "2026-08-28"
    assert briefing["dia_semana"] == "VIERNES"
    assert "metricas" in briefing
    assert "resumen_telegram" in briefing
    assert "Preparar parcial de Bases de Datos" in briefing["resumen_telegram"]

    # 3. Limpieza
    client.delete(f"/api/v1/tareas/{id_tarea}")
