from collections.abc import Generator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.adapters.controllers.dependencies import get_planificacion_controller
from src.adapters.controllers.planificacion_controller import (
    PlanificacionController,
)
from src.adapters.gateways.planificacion.yaml_planificacion_gateway import (
    YamlPlanificacionGateway,
)
from src.application.use_cases.planificacion.actualizar_estado_tarea_plan_use_case import (
    ActualizarEstadoTareaPlanUseCase,
)
from src.application.use_cases.planificacion.obtener_tablero_kanban_pert_use_case import (
    ObtenerTableroKanbanPertUseCase,
)
from src.main import app

YAML_TEST_CONTENT = """id_plan: test_plan
titulo: Plan de Prueba
descripcion: Plan para test de integración
version: "1.0"
tareas:
  - id: T1
    titulo: Tarea 1
    descripcion: Primera tarea
    optimista: 1.0
    mas_probable: 2.0
    pesimista: 3.0
    predecesores: []
    estado: PENDIENTE
    responsable: Tester
    fase: QA
  - id: T2
    titulo: Tarea 2
    descripcion: Segunda tarea
    optimista: 2.0
    mas_probable: 4.0
    pesimista: 6.0
    predecesores:
      - T1
    estado: PENDIENTE
    responsable: Dev
    fase: Dev
"""


@pytest.fixture
def plan_test_client(tmp_path: Path) -> Generator[TestClient, None, None]:
    yaml_file = tmp_path / "test_plan.yaml"
    yaml_file.write_text(YAML_TEST_CONTENT, encoding="utf-8")

    gateway = YamlPlanificacionGateway(data_dir=tmp_path)
    controller = PlanificacionController(
        obtener_tablero_uc=ObtenerTableroKanbanPertUseCase(repository=gateway),
        actualizar_estado_uc=ActualizarEstadoTareaPlanUseCase(repository=gateway),
    )
    app.dependency_overrides[get_planificacion_controller] = lambda: controller
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_planificacion_controller, None)


def test_get_tablero_kanban_vaca_muerta(client: TestClient) -> None:
    """Verifica que el endpoint real obtenga el plan de Vaca Muerta con sus 14 tareas y PERT."""
    response = client.get("/api/v1/planificacion/kanban?id_plan=vaca_muerta")
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert data["id_plan"] == "vaca_muerta"
    assert "Vaca Muerta" in data["titulo_plan"]

    # Verificar estructura Kanban
    total_tareas = (
        len(data["pendientes"]) + len(data["en_proceso"]) + len(data["finalizadas"])
    )
    assert total_tareas == 14

    # Verificar métricas PERT
    metricas = data["metricas"]
    assert metricas["duracion_esperada"] > 30.0
    assert len(metricas["camino_critico"]) >= 5
    assert "A1" in metricas["camino_critico"]

    # Verificar diagrama Mermaid
    assert "graph LR" in data["diagrama_mermaid"]


def test_get_tablero_kanban_plan_inexistente(client: TestClient) -> None:
    """Verifica respuesta 404 al solicitar un plan que no existe."""
    response = client.get("/api/v1/planificacion/kanban?id_plan=no_existe_este_plan")
    assert response.status_code == 404

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PLAN_NO_ENCONTRADO"


def test_patch_estado_tarea_success(plan_test_client: TestClient) -> None:
    """Verifica cambio de estado de una tarea y recálculo en el plan de prueba."""
    # Cambiar T1 a EN_PROCESO
    response = plan_test_client.patch(
        "/api/v1/planificacion/tareas/T1/estado?id_plan=test_plan",
        json={"estado": "EN_PROCESO"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    data = body["data"]

    # T1 debe estar en en_proceso
    ids_en_proceso = [t["id"] for t in data["en_proceso"]]
    assert "T1" in ids_en_proceso

    # Cambiar T1 a COMPLETADA
    response_fin = plan_test_client.patch(
        "/api/v1/planificacion/tareas/T1/estado?id_plan=test_plan",
        json={"estado": "COMPLETADA"},
    )
    assert response_fin.status_code == 200
    data_fin = response_fin.json()["data"]
    ids_finalizadas = [t["id"] for t in data_fin["finalizadas"]]
    assert "T1" in ids_finalizadas


def test_patch_estado_tarea_inexistente(plan_test_client: TestClient) -> None:
    """Verifica respuesta 404 al intentar cambiar estado de tarea que no existe."""
    response = plan_test_client.patch(
        "/api/v1/planificacion/tareas/TAREA_FANTASMA/estado?id_plan=test_plan",
        json={"estado": "COMPLETADA"},
    )
    assert response.status_code == 404

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "TAREA_PLAN_NO_ENCONTRADA"


def test_patch_estado_tarea_invalido(plan_test_client: TestClient) -> None:
    """Verifica error de validación 422 al enviar un estado inexistente."""
    response = plan_test_client.patch(
        "/api/v1/planificacion/tareas/T1/estado?id_plan=test_plan",
        json={"estado": "ESTADO_INVENTADO"},
    )
    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "TAREA_PLAN_INVALIDA"
