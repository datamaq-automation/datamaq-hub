"""Mapper between planificacion domain entities and Pydantic DTOs."""

from src.application.dtos.planificacion_dtos import (
    EstimacionPertDTO,
    MetricasProyectoDTO,
    TableroKanbanDTO,
    TareaPlanDTO,
    TiemposCpmDTO,
)
from src.domain.planificacion.entities import (
    MetricasProyecto,
    TableroKanban,
    TareaPlan,
)


class PlanificacionMapper:
    """Mapea bidireccionalmente entre entidades de dominio y DTOs de planificación."""

    @classmethod
    def tarea_entidad_a_dto(cls, tarea: TareaPlan) -> TareaPlanDTO:
        """Convierte una entidad TareaPlan a TareaPlanDTO."""
        return TareaPlanDTO(
            id=tarea.id,
            titulo=tarea.titulo,
            descripcion=tarea.descripcion,
            fase=tarea.fase,
            estado=tarea.estado.value,
            predecesores=list(tarea.predecesores),
            estimacion=EstimacionPertDTO(
                optimista=tarea.estimacion.optimista,
                mas_probable=tarea.estimacion.mas_probable,
                pesimista=tarea.estimacion.pesimista,
                esperada=tarea.estimacion.esperada,
                varianza=tarea.estimacion.varianza,
            ),
            tiempos=TiemposCpmDTO(
                early_start=tarea.tiempos.early_start,
                early_finish=tarea.tiempos.early_finish,
                late_start=tarea.tiempos.late_start,
                late_finish=tarea.tiempos.late_finish,
                holgura_total=tarea.tiempos.holgura_total,
            ),
            es_critica=tarea.es_critica,
            es_subcritica=tarea.es_subcritica,
            responsable=tarea.responsable,
        )

    @classmethod
    def metricas_entidad_a_dto(cls, metricas: MetricasProyecto) -> MetricasProyectoDTO:
        """Convierte una entidad MetricasProyecto a MetricasProyectoDTO."""
        return MetricasProyectoDTO(
            duracion_esperada=metricas.duracion_esperada,
            varianza_total=metricas.varianza_total,
            desviacion_estandar=metricas.desviacion_estandar,
            intervalo_confianza_95_min=metricas.intervalo_confianza_95_min,
            intervalo_confianza_95_max=metricas.intervalo_confianza_95_max,
            camino_critico=list(metricas.camino_critico),
            camino_subcritico=list(metricas.camino_subcritico),
            total_tareas=metricas.total_tareas,
            tareas_pendientes=metricas.tareas_pendientes,
            tareas_en_proceso=metricas.tareas_en_proceso,
            tareas_completadas=metricas.tareas_completadas,
            porcentaje_avance=metricas.porcentaje_avance,
        )

    @classmethod
    def tablero_entidad_a_dto(cls, tablero: TableroKanban) -> TableroKanbanDTO:
        """Convierte una entidad TableroKanban a TableroKanbanDTO."""
        return TableroKanbanDTO(
            id_plan=tablero.id_plan,
            titulo_plan=tablero.titulo_plan,
            descripcion_plan=tablero.descripcion_plan,
            pendientes=[cls.tarea_entidad_a_dto(t) for t in tablero.pendientes],
            en_proceso=[cls.tarea_entidad_a_dto(t) for t in tablero.en_proceso],
            finalizadas=[cls.tarea_entidad_a_dto(t) for t in tablero.finalizadas],
            metricas=cls.metricas_entidad_a_dto(tablero.metricas),
            diagrama_mermaid=tablero.diagrama_mermaid,
        )
