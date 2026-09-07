"""Unit tests for PlanificacionController."""

from src.adapters.controllers.planificacion_controller import PlanificacionController
from src.application.use_cases.planificacion.actualizar_estado_tarea_plan_use_case import (
    ActualizarEstadoTareaPlanUseCase,
)
from src.application.use_cases.planificacion.obtener_tablero_kanban_pert_use_case import (
    ObtenerTableroKanbanPertUseCase,
)
from tests.unit.test_planificacion_use_cases import FakePlanificacionRepository


def test_planificacion_controller_obtener_tablero() -> None:
    repo = FakePlanificacionRepository()
    controller = PlanificacionController(
        obtener_tablero_uc=ObtenerTableroKanbanPertUseCase(repository=repo),
        actualizar_estado_uc=ActualizarEstadoTareaPlanUseCase(repository=repo),
    )

    dto = controller.obtener_tablero("test_plan")
    assert dto.id_plan == "test_plan"
    assert len(dto.pendientes) == 1
    assert dto.pendientes[0].id == "T1"


def test_planificacion_controller_actualizar_estado() -> None:
    repo = FakePlanificacionRepository()
    controller = PlanificacionController(
        obtener_tablero_uc=ObtenerTableroKanbanPertUseCase(repository=repo),
        actualizar_estado_uc=ActualizarEstadoTareaPlanUseCase(repository=repo),
    )

    dto = controller.actualizar_estado_tarea("T1", "EN_PROCESO", "test_plan")
    assert len(dto.pendientes) == 0
    assert len(dto.en_proceso) == 1
    assert dto.en_proceso[0].id == "T1"
