"""Pruebas de integración para las rutas de tareas /api/v1/tareas."""

from starlette.testclient import TestClient


def test_flujo_crud_completo_tareas(client: TestClient) -> None:
    # 1. Crear tarea
    payload = {
        "titulo": "Preparar material de Redes Neuronales",
        "descripcion": "Unidad 4: Backpropagation y Optimizadores",
        "fecha_limite": "2026-09-10",
        "prioridad": "ALTA",
        "categoria": "DOCENCIA",
        "docente_cuit": "20-36528392-4",
        "tags": ["ia", "docencia", "clases"],
    }
    resp = client.post("/api/v1/tareas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    tarea = data["data"]
    id_tarea = tarea["id_tarea"]
    assert tarea["titulo"] == "Preparar material de Redes Neuronales"
    assert tarea["estado"] == "PENDIENTE"
    assert tarea["docente_cuit"] == "20365283924"

    # 2. Obtener tarea por ID
    resp_get = client.get(f"/api/v1/tareas/{id_tarea}")
    assert resp_get.status_code == 200
    assert resp_get.json()["data"]["id_tarea"] == id_tarea

    # 3. Listar tareas con filtros
    resp_list = client.get("/api/v1/tareas?categoria=DOCENCIA&cuit=20365283924")
    assert resp_list.status_code == 200
    list_data = resp_list.json()["data"]
    assert list_data["total"] >= 1
    assert any(t["id_tarea"] == id_tarea for t in list_data["tareas"])

    # 4. Modificar tarea (PATCH)
    resp_patch = client.patch(
        f"/api/v1/tareas/{id_tarea}",
        json={
            "prioridad": "URGENTE",
            "descripcion": "Unidad 4 ampliada con Transformers",
        },
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["data"]["prioridad"] == "URGENTE"
    assert (
        resp_patch.json()["data"]["descripcion"] == "Unidad 4 ampliada con Transformers"
    )

    # 5. Marcar como completada
    resp_comp = client.post(f"/api/v1/tareas/{id_tarea}/completar")
    assert resp_comp.status_code == 200
    assert resp_comp.json()["data"]["estado"] == "COMPLETADA"
    assert resp_comp.json()["data"]["fecha_completada"] is not None

    # 6. Eliminar tarea
    resp_del = client.delete(f"/api/v1/tareas/{id_tarea}")
    assert resp_del.status_code == 200
    assert resp_del.json()["data"]["eliminado"] is True

    # 7. Verificar 404 al consultar eliminada
    resp_404 = client.get(f"/api/v1/tareas/{id_tarea}")
    assert resp_404.status_code == 404
