"""Data Transfer Objects (DTOs) for planificacion bounded context."""

from pydantic import BaseModel, ConfigDict, Field


class EstimacionPertDTO(BaseModel):
    """DTO para estimaciones probabilísticas de duración PERT."""

    model_config = ConfigDict(frozen=True)

    optimista: float = Field(..., description="Tiempo optimista (días)")
    mas_probable: float = Field(..., description="Tiempo más probable (días)")
    pesimista: float = Field(..., description="Tiempo pesimista (días)")
    esperada: float = Field(..., description="Tiempo esperado Te = (o + 4m + p)/6")
    varianza: float = Field(..., description="Varianza sigma^2 = ((p - o)/6)^2")


class TiemposCpmDTO(BaseModel):
    """DTO para tiempos calculados por el método de camino crítico (CPM)."""

    model_config = ConfigDict(frozen=True)

    early_start: float = Field(..., description="Inicio más temprano (ES)")
    early_finish: float = Field(..., description="Finalización más temprana (EF)")
    late_start: float = Field(..., description="Inicio más tardío (LS)")
    late_finish: float = Field(..., description="Finalización más tardía (LF)")
    holgura_total: float = Field(..., description="Holgura total H_T = LS - ES")


class TareaPlanDTO(BaseModel):
    """DTO representativo de una tarea dentro del tablero Kanban y grafo PERT."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Identificador único de la tarea (ej. A1)")
    titulo: str = Field(..., description="Título de la tarea")
    descripcion: str = Field(default="", description="Descripción detallada")
    fase: str = Field(default="", description="Fase o hito del proyecto")
    estado: str = Field(
        ..., description="Estado Kanban: PENDIENTE, EN_PROCESO, COMPLETADA"
    )
    predecesores: list[str] = Field(
        default_factory=list[str], description="IDs de tareas predecesoras inmediatas"
    )
    estimacion: EstimacionPertDTO = Field(
        ..., description="Parámetros PERT de la tarea"
    )
    tiempos: TiemposCpmDTO = Field(..., description="Tiempos y holguras CPM")
    es_critica: bool = Field(
        default=False,
        description="Indica si la tarea pertenece al camino crítico (holgura = 0)",
    )
    es_subcritica: bool = Field(
        default=False,
        description="Indica si la tarea es subcrítica (0 < holgura <= 1d)",
    )
    responsable: str = Field(default="", description="Responsable asignado a la tarea")


class MetricasProyectoDTO(BaseModel):
    """DTO para métricas consolidadas del proyecto y de incertidumbre estadística."""

    model_config = ConfigDict(frozen=True)

    duracion_esperada: float = Field(
        ..., description="Duración total esperada del proyecto (días hábiles)"
    )
    varianza_total: float = Field(
        ..., description="Varianza acumulada sobre el camino crítico"
    )
    desviacion_estandar: float = Field(
        ..., description="Desviación estándar de la duración total"
    )
    intervalo_confianza_95_min: float = Field(
        ..., description="Límite inferior del intervalo de confianza al 95% (días)"
    )
    intervalo_confianza_95_max: float = Field(
        ..., description="Límite superior del intervalo de confianza al 95% (días)"
    )
    camino_critico: list[str] = Field(
        default_factory=list[str], description="Secuencia de IDs en el camino crítico"
    )
    camino_subcritico: list[str] = Field(
        default_factory=list[str], description="Secuencia de IDs en rutas subcríticas"
    )
    total_tareas: int = Field(..., description="Cantidad total de tareas")
    tareas_pendientes: int = Field(..., description="Cantidad de tareas pendientes")
    tareas_en_proceso: int = Field(..., description="Cantidad de tareas en proceso")
    tareas_completadas: int = Field(..., description="Cantidad de tareas finalizadas")
    porcentaje_avance: float = Field(
        ..., description="Porcentaje de avance total completado"
    )


class TableroKanbanDTO(BaseModel):
    """DTO para el tablero Kanban completo con red PERT integrada."""

    model_config = ConfigDict(frozen=True)

    id_plan: str = Field(..., description="Identificador del plan de proyecto")
    titulo_plan: str = Field(..., description="Título del plan")
    descripcion_plan: str = Field(default="", description="Descripción del plan")
    pendientes: list[TareaPlanDTO] = Field(
        default_factory=list[TareaPlanDTO], description="Tareas en estado PENDIENTE"
    )
    en_proceso: list[TareaPlanDTO] = Field(
        default_factory=list[TareaPlanDTO], description="Tareas en estado EN_PROCESO"
    )
    finalizadas: list[TareaPlanDTO] = Field(
        default_factory=list[TareaPlanDTO], description="Tareas en estado COMPLETADA"
    )
    metricas: MetricasProyectoDTO = Field(
        ..., description="Métricas estadísticas PERT-CPM"
    )
    diagrama_mermaid: str = Field(
        default="", description="Código del diagrama de red Mermaid renderizable"
    )


class CambiarEstadoTareaPlanDTO(BaseModel):
    """DTO para actualizar el estado de una tarea en el tablero Kanban."""

    estado: str = Field(
        ..., description="Nuevo estado: PENDIENTE, EN_PROCESO, COMPLETADA"
    )
