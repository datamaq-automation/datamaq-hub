"""Entities for planificacion bounded context."""

from dataclasses import dataclass, field
from typing import Any

from src.domain.planificacion.exceptions import TareaPlanInvalidaError
from src.domain.planificacion.value_objects import EstadoTareaPlan


@dataclass(frozen=True)
class EstimacionPert:
    """Valores de estimación probabilística de una tarea."""

    optimista: float
    mas_probable: float
    pesimista: float
    esperada: float = 0.0
    varianza: float = 0.0

    def __post_init__(self) -> None:
        if self.optimista < 0 or self.mas_probable < 0 or self.pesimista < 0:
            raise TareaPlanInvalidaError(
                "Las estimaciones temporales no pueden ser negativas."
            )
        if self.optimista > self.mas_probable or self.mas_probable > self.pesimista:
            raise TareaPlanInvalidaError(
                f"Las estimaciones deben cumplir optimista ({self.optimista}) <= más probable ({self.mas_probable}) <= pesimista ({self.pesimista})."
            )


@dataclass(frozen=True)
class TiemposCpm:
    """Tiempos calculados por el método de camino crítico (CPM)."""

    early_start: float = 0.0
    early_finish: float = 0.0
    late_start: float = 0.0
    late_finish: float = 0.0
    holgura_total: float = 0.0


@dataclass(frozen=True)
class TareaPlan:
    """Representa una tarea planificada dentro de una red de proyecto y tablero Kanban."""

    id: str
    titulo: str
    descripcion: str = ""
    fase: str = ""
    estado: EstadoTareaPlan = EstadoTareaPlan.PENDIENTE
    predecesores: tuple[str, ...] = ()
    estimacion: EstimacionPert = field(
        default_factory=lambda: EstimacionPert(0.0, 0.0, 0.0)
    )
    tiempos: TiemposCpm = field(default_factory=TiemposCpm)
    es_critica: bool = False
    es_subcritica: bool = False
    responsable: str = ""
    metadatos: dict[str, Any] = field(default_factory=dict[str, Any])

    def con_estado(self, nuevo_estado: EstadoTareaPlan) -> "TareaPlan":
        """Devuelve una nueva instancia con el estado actualizado."""
        return TareaPlan(
            id=self.id,
            titulo=self.titulo,
            descripcion=self.descripcion,
            fase=self.fase,
            estado=nuevo_estado,
            predecesores=self.predecesores,
            estimacion=self.estimacion,
            tiempos=self.tiempos,
            es_critica=self.es_critica,
            es_subcritica=self.es_subcritica,
            responsable=self.responsable,
            metadatos=self.metadatos,
        )


@dataclass(frozen=True)
class MetricasProyecto:
    """Métricas globales y estadísticas de la red PERT y avance Kanban."""

    duracion_esperada: float = 0.0
    varianza_total: float = 0.0
    desviacion_estandar: float = 0.0
    intervalo_confianza_95_min: float = 0.0
    intervalo_confianza_95_max: float = 0.0
    camino_critico: tuple[str, ...] = ()
    camino_subcritico: tuple[str, ...] = ()
    total_tareas: int = 0
    tareas_pendientes: int = 0
    tareas_en_proceso: int = 0
    tareas_completadas: int = 0
    porcentaje_avance: float = 0.0


@dataclass(frozen=True)
class TableroKanban:
    """Agregado que contiene las tareas agrupadas por estado Kanban y métricas PERT-CPM."""

    id_plan: str
    titulo_plan: str
    descripcion_plan: str = ""
    pendientes: tuple[TareaPlan, ...] = ()
    en_proceso: tuple[TareaPlan, ...] = ()
    finalizadas: tuple[TareaPlan, ...] = ()
    metricas: MetricasProyecto = field(default_factory=MetricasProyecto)
    diagrama_mermaid: str = ""
