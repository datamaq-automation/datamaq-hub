"""Unit tests for YamlPlanificacionGateway."""

from pathlib import Path

import pytest

from src.adapters.gateways.planificacion.yaml_planificacion_gateway import (
    YamlPlanificacionGateway,
)
from src.domain.planificacion.exceptions import (
    PlanNoEncontradoError,
    TareaPlanNoEncontradaError,
)
from src.domain.planificacion.value_objects import EstadoTareaPlan


def test_yaml_planificacion_gateway_carga_vaca_muerta() -> None:
    """Verifica la carga del plan real de Vaca Muerta desde data/pert/camino_critico_vaca_muerta.yaml."""
    gateway = YamlPlanificacionGateway()
    tablero = gateway.obtener_tablero("vaca_muerta")

    assert tablero.id_plan == "vaca_muerta"
    assert tablero.metricas.total_tareas == 14
    assert tablero.metricas.duracion_esperada == 36.53
    assert tablero.metricas.camino_critico == (
        "A1",
        "A2",
        "B2",
        "C1",
        "C2",
        "D1",
        "D2",
        "D3",
        "E1",
        "E2",
    )
    # A3 ya fue marcada como COMPLETADA
    assert any(t.id == "A3" for t in tablero.finalizadas)
    assert len(tablero.pendientes) == 13
    assert len(tablero.en_proceso) == 0


def test_yaml_planificacion_gateway_actualizar_estado(tmp_path: Path) -> None:
    """Verifica que actualizar el estado modifique el archivo y recalcule el tablero."""
    yaml_content = """id_plan: test_update
titulo: Test Update
tareas:
  - id: T1
    titulo: Tarea 1
    estado: PENDIENTE
    predecesores: []
    optimista: 1.0
    mas_probable: 1.0
    pesimista: 1.0
  - id: T2
    titulo: Tarea 2
    estado: PENDIENTE
    predecesores: [T1]
    optimista: 2.0
    mas_probable: 2.0
    pesimista: 2.0
"""
    file_path = tmp_path / "test_update.yaml"
    file_path.write_text(yaml_content, encoding="utf-8")

    gateway = YamlPlanificacionGateway(data_dir=tmp_path)

    # Inicialmente ambas pendientes
    tablero_inicial = gateway.obtener_tablero("test_update")
    assert len(tablero_inicial.pendientes) == 2
    assert len(tablero_inicial.finalizadas) == 0

    # Mover T1 a COMPLETADA
    tablero_actualizado = gateway.actualizar_estado_tarea(
        id_tarea="T1",
        nuevo_estado=EstadoTareaPlan.COMPLETADA,
        id_plan="test_update",
    )

    assert len(tablero_actualizado.pendientes) == 1
    assert len(tablero_actualizado.finalizadas) == 1
    assert tablero_actualizado.finalizadas[0].id == "T1"
    assert tablero_actualizado.metricas.porcentaje_avance == 50.0

    # Verificar persistencia en disco
    nuevo_gateway = YamlPlanificacionGateway(data_dir=tmp_path)
    tablero_disco = nuevo_gateway.obtener_tablero("test_update")
    assert len(tablero_disco.finalizadas) == 1


def test_yaml_planificacion_gateway_plan_no_encontrado(tmp_path: Path) -> None:
    """Verifica que se lance PlanNoEncontradoError si el plan no existe."""
    gateway = YamlPlanificacionGateway(data_dir=tmp_path)
    with pytest.raises(PlanNoEncontradoError):
        gateway.obtener_tablero("inexistente")


def test_yaml_planificacion_gateway_tarea_no_encontrada(tmp_path: Path) -> None:
    """Verifica que se lance TareaPlanNoEncontradaError si la tarea a actualizar no existe."""
    yaml_content = """id_plan: test_err
titulo: Test
tareas:
  - id: T1
    titulo: Tarea 1
    estado: PENDIENTE
    predecesores: []
    optimista: 1.0
    mas_probable: 1.0
    pesimista: 1.0
"""
    (tmp_path / "test_err.yaml").write_text(yaml_content, encoding="utf-8")
    gateway = YamlPlanificacionGateway(data_dir=tmp_path)

    with pytest.raises(TareaPlanNoEncontradaError):
        gateway.actualizar_estado_tarea(
            "FANTASMA", EstadoTareaPlan.COMPLETADA, "test_err"
        )
