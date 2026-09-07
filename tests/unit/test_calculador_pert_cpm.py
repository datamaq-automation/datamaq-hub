"""Unit tests for CalculadorPertCpmService."""

import pytest

from src.domain.planificacion.entities import EstimacionPert, TareaPlan
from src.domain.planificacion.exceptions import (
    CicloEnGrafoPertError,
    TareaPlanInvalidaError,
)
from src.domain.planificacion.services import CalculadorPertCpmService
from src.domain.planificacion.value_objects import EstadoTareaPlan


def test_calculo_red_lineal_simple() -> None:
    """Verifica el cálculo de una red de 3 tareas secuenciales."""
    t1 = TareaPlan(
        id="T1",
        titulo="Tarea 1",
        estimacion=EstimacionPert(1.0, 1.0, 1.0),  # Te = 1.0, var = 0
    )
    t2 = TareaPlan(
        id="T2",
        titulo="Tarea 2",
        predecesores=("T1",),
        estimacion=EstimacionPert(2.0, 2.0, 2.0),  # Te = 2.0, var = 0
    )
    t3 = TareaPlan(
        id="T3",
        titulo="Tarea 3",
        predecesores=("T2",),
        estimacion=EstimacionPert(3.0, 3.0, 3.0),  # Te = 3.0, var = 0
    )

    tablero = CalculadorPertCpmService.calcular_tablero(
        id_plan="test",
        titulo_plan="Plan Test",
        descripcion_plan="Test",
        tareas_raw=[t1, t2, t3],
    )

    assert tablero.metricas.duracion_esperada == 6.0
    assert tablero.metricas.camino_critico == ("T1", "T2", "T3")
    assert len(tablero.pendientes) == 3


def test_calculo_bifurcacion_y_convergencia() -> None:
    """Verifica el cálculo de holguras con caminos paralelos de distinta duración."""
    # A (2d) -> B (4d) -> D (1d) => Ruta 1: 2 + 4 + 1 = 7d (Crítica)
    # A (2d) -> C (1d) -> D (1d) => Ruta 2: 2 + 1 + 1 = 4d (Holgura = 3d)
    a = TareaPlan(id="A", titulo="A", estimacion=EstimacionPert(2.0, 2.0, 2.0))
    b = TareaPlan(
        id="B",
        titulo="B",
        predecesores=("A",),
        estimacion=EstimacionPert(4.0, 4.0, 4.0),
    )
    c = TareaPlan(
        id="C",
        titulo="C",
        predecesores=("A",),
        estimacion=EstimacionPert(1.0, 1.0, 1.0),
    )
    d = TareaPlan(
        id="D",
        titulo="D",
        predecesores=("B", "C"),
        estimacion=EstimacionPert(1.0, 1.0, 1.0),
    )

    tablero = CalculadorPertCpmService.calcular_tablero(
        id_plan="test_diamond",
        titulo_plan="Diamond Test",
        descripcion_plan="",
        tareas_raw=[a, b, c, d],
    )

    assert tablero.metricas.duracion_esperada == 7.0
    assert tablero.metricas.camino_critico == ("A", "B", "D")

    # Verificar tiempos específicos de C
    tarea_c = next(t for t in tablero.pendientes if t.id == "C")
    assert tarea_c.tiempos.early_start == 2.0
    assert tarea_c.tiempos.early_finish == 3.0
    assert tarea_c.tiempos.late_start == 5.0
    assert tarea_c.tiempos.late_finish == 6.0
    assert tarea_c.tiempos.holgura_total == 3.0
    assert not tarea_c.es_critica


def test_detecta_ciclo_en_red_pert() -> None:
    """Verifica que se lance CicloEnGrafoPertError ante una dependencia circular."""
    t1 = TareaPlan(
        id="A",
        titulo="A",
        predecesores=("B",),
        estimacion=EstimacionPert(1.0, 1.0, 1.0),
    )
    t2 = TareaPlan(
        id="B",
        titulo="B",
        predecesores=("A",),
        estimacion=EstimacionPert(1.0, 1.0, 1.0),
    )

    with pytest.raises(CicloEnGrafoPertError):
        CalculadorPertCpmService.calcular_tablero(
            id_plan="ciclo",
            titulo_plan="Ciclo",
            descripcion_plan="",
            tareas_raw=[t1, t2],
        )


def test_detecta_predecesor_inexistente() -> None:
    """Verifica que se lance TareaPlanInvalidaError si se referencia un ID que no existe."""
    t1 = TareaPlan(
        id="A",
        titulo="A",
        predecesores=("FANTASMA",),
        estimacion=EstimacionPert(1.0, 1.0, 1.0),
    )

    with pytest.raises(TareaPlanInvalidaError):
        CalculadorPertCpmService.calcular_tablero(
            id_plan="test",
            titulo_plan="Test",
            descripcion_plan="",
            tareas_raw=[t1],
        )


def test_distribucion_columnas_kanban() -> None:
    """Verifica que las tareas se clasifiquen correctamente en pendientes, en proceso y finalizadas."""
    t1 = TareaPlan(
        id="A",
        titulo="A",
        estado=EstadoTareaPlan.COMPLETADA,
        estimacion=EstimacionPert(1.0, 1.0, 1.0),
    )
    t2 = TareaPlan(
        id="B",
        titulo="B",
        predecesores=("A",),
        estado=EstadoTareaPlan.EN_PROCESO,
        estimacion=EstimacionPert(2.0, 2.0, 2.0),
    )
    t3 = TareaPlan(
        id="C",
        titulo="C",
        predecesores=("B",),
        estado=EstadoTareaPlan.PENDIENTE,
        estimacion=EstimacionPert(1.0, 1.0, 1.0),
    )

    tablero = CalculadorPertCpmService.calcular_tablero(
        id_plan="kanban",
        titulo_plan="Kanban",
        descripcion_plan="",
        tareas_raw=[t1, t2, t3],
    )

    assert len(tablero.finalizadas) == 1
    assert tablero.finalizadas[0].id == "A"
    assert len(tablero.en_proceso) == 1
    assert tablero.en_proceso[0].id == "B"
    assert len(tablero.pendientes) == 1
    assert tablero.pendientes[0].id == "C"

    assert tablero.metricas.total_tareas == 3
    assert tablero.metricas.tareas_completadas == 1
    assert tablero.metricas.porcentaje_avance == 33.3
    assert "graph LR" in tablero.diagrama_mermaid
    assert "classDef completed" in tablero.diagrama_mermaid
