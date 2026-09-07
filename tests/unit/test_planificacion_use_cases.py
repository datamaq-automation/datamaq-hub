"""Unit tests for planificacion application use cases."""

import pytest

from src.application.use_cases.planificacion.actualizar_estado_tarea_plan_use_case import (
    ActualizarEstadoTareaPlanUseCase,
)
from src.application.use_cases.planificacion.obtener_tablero_kanban_pert_use_case import (
    ObtenerTableroKanbanPertUseCase,
)
from src.domain.planificacion.entities import (
    EstimacionPert,
    MetricasProyecto,
    TableroKanban,
    TareaPlan,
)
from src.domain.planificacion.exceptions import TareaPlanInvalidaError
from src.domain.planificacion.ports import PlanificacionRepositoryPort
from src.domain.planificacion.value_objects import EstadoTareaPlan


class FakePlanificacionRepository(PlanificacionRepositoryPort):
    """Repositorio en memoria para tests unitarios de casos de uso."""

    def __init__(self) -> None:
        self.tarea = TareaPlan(
            id="T1",
            titulo="Tarea Test",
            estado=EstadoTareaPlan.PENDIENTE,
            estimacion=EstimacionPert(1.0, 1.0, 1.0, esperada=1.0, varianza=0.0),
        )

    def obtener_tablero(self, id_plan: str = "vaca_muerta") -> TableroKanban:
        return TableroKanban(
            id_plan=id_plan,
            titulo_plan="Plan Fake",
            descripcion_plan="",
            pendientes=(self.tarea,)
            if self.tarea.estado == EstadoTareaPlan.PENDIENTE
            else (),
            en_proceso=(self.tarea,)
            if self.tarea.estado == EstadoTareaPlan.EN_PROCESO
            else (),
            finalizadas=(self.tarea,)
            if self.tarea.estado == EstadoTareaPlan.COMPLETADA
            else (),
            metricas=MetricasProyecto(total_tareas=1, duracion_esperada=1.0),
            diagrama_mermaid="graph LR\n    START --> T1",
        )

    def actualizar_estado_tarea(
        self,
        id_tarea: str,
        nuevo_estado: EstadoTareaPlan,
        id_plan: str = "vaca_muerta",
    ) -> TableroKanban:
        self.tarea = self.tarea.con_estado(nuevo_estado)
        return self.obtener_tablero(id_plan)


def test_obtener_tablero_use_case() -> None:
    repo = FakePlanificacionRepository()
    use_case = ObtenerTableroKanbanPertUseCase(repository=repo)
    dto = use_case.execute("fake_plan")

    assert dto.id_plan == "fake_plan"
    assert len(dto.pendientes) == 1
    assert dto.pendientes[0].id == "T1"
    assert dto.pendientes[0].estado == "PENDIENTE"
    assert dto.metricas.duracion_esperada == 1.0


def test_actualizar_estado_tarea_use_case() -> None:
    repo = FakePlanificacionRepository()
    use_case = ActualizarEstadoTareaPlanUseCase(repository=repo)

    dto = use_case.execute(
        id_tarea="T1", nuevo_estado_str="COMPLETADA", id_plan="fake_plan"
    )

    assert len(dto.pendientes) == 0
    assert len(dto.finalizadas) == 1
    assert dto.finalizadas[0].id == "T1"
    assert dto.finalizadas[0].estado == "COMPLETADA"


def test_actualizar_estado_tarea_invalido() -> None:
    repo = FakePlanificacionRepository()
    use_case = ActualizarEstadoTareaPlanUseCase(repository=repo)

    with pytest.raises(TareaPlanInvalidaError):
        use_case.execute(id_tarea="T1", nuevo_estado_str="ESTADO_INEXISTENTE")
