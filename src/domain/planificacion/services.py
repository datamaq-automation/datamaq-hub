"""Domain service for calculating PERT and CPM network metrics and Kanban boards."""

import math
from collections import defaultdict, deque
from collections.abc import Sequence

from src.domain.planificacion.entities import (
    EstimacionPert,
    MetricasProyecto,
    TableroKanban,
    TareaPlan,
    TiemposCpm,
)
from src.domain.planificacion.exceptions import (
    CicloEnGrafoPertError,
    TareaPlanInvalidaError,
)
from src.domain.planificacion.value_objects import EstadoTareaPlan


class CalculadorPertCpmService:
    """Servicio de dominio para resolución de redes PERT/CPM y tableros Kanban."""

    @classmethod
    def calcular_tablero(
        cls,
        id_plan: str,
        titulo_plan: str,
        descripcion_plan: str,
        tareas_raw: Sequence[TareaPlan],
    ) -> TableroKanban:
        """Calcula el pase hacia adelante, pase hacia atrás, holguras y métricas de red."""
        if not tareas_raw:
            return TableroKanban(
                id_plan=id_plan,
                titulo_plan=titulo_plan,
                descripcion_plan=descripcion_plan,
                pendientes=(),
                en_proceso=(),
                finalizadas=(),
                metricas=MetricasProyecto(),
                diagrama_mermaid="graph LR\n    START((Inicio))",
            )

        tareas_map: dict[str, TareaPlan] = {t.id: t for t in tareas_raw}

        # Validar consistencia de predecesores
        for tarea in tareas_raw:
            for pred in tarea.predecesores:
                if pred not in tareas_map:
                    raise TareaPlanInvalidaError(
                        f"La tarea '{tarea.id}' tiene un predecesor inexistente: '{pred}'"
                    )

        # Calcular estimaciones PERT (Te, varianza)
        estimaciones: dict[str, EstimacionPert] = {}
        for t in tareas_raw:
            o = t.estimacion.optimista
            m = t.estimacion.mas_probable
            p = t.estimacion.pesimista
            te = round((o + 4.0 * m + p) / 6.0, 2)
            var = round(((p - o) / 6.0) ** 2, 4)
            estimaciones[t.id] = EstimacionPert(
                optimista=o,
                mas_probable=m,
                pesimista=p,
                esperada=te,
                varianza=var,
            )

        # Orden topológico (Algoritmo de Kahn)
        in_degree: dict[str, int] = {t.id: len(t.predecesores) for t in tareas_raw}
        successors: dict[str, list[str]] = defaultdict(list)
        for t in tareas_raw:
            for pred in t.predecesores:
                successors[pred].append(t.id)

        queue: deque[str] = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        orden_topologico: list[str] = []

        while queue:
            curr = queue.popleft()
            orden_topologico.append(curr)
            for succ in successors[curr]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(orden_topologico) != len(tareas_raw):
            raise CicloEnGrafoPertError(
                "Se ha detectado un ciclo o dependencia circular en la red PERT."
            )

        # 1. Forward Pass (Pase hacia adelante: ES, EF)
        early_start: dict[str, float] = {}
        early_finish: dict[str, float] = {}

        for t_id in orden_topologico:
            tarea = tareas_map[t_id]
            te = estimaciones[t_id].esperada
            if not tarea.predecesores:
                es = 0.0
            else:
                es = max(early_finish[p] for p in tarea.predecesores)
            ef = round(es + te, 2)
            early_start[t_id] = round(es, 2)
            early_finish[t_id] = ef

        duracion_proyecto = max(early_finish.values()) if early_finish else 0.0
        duracion_proyecto = round(duracion_proyecto, 2)

        # 2. Backward Pass (Pase hacia atrás: LF, LS)
        late_start: dict[str, float] = {}
        late_finish: dict[str, float] = {}

        for t_id in reversed(orden_topologico):
            te = estimaciones[t_id].esperada
            succs = successors[t_id]
            if not succs:
                lf = duracion_proyecto
            else:
                lf = min(late_start[s] for s in succs)
            ls = round(lf - te, 2)
            late_finish[t_id] = round(lf, 2)
            late_start[t_id] = ls

        # 3. Holguras y clasificación de criticidad
        tiempos: dict[str, TiemposCpm] = {}
        es_critica_map: dict[str, bool] = {}
        es_subcritica_map: dict[str, bool] = {}

        for t_id in orden_topologico:
            es = early_start[t_id]
            ef = early_finish[t_id]
            ls = late_start[t_id]
            lf = late_finish[t_id]
            holgura = round(ls - es, 2)
            # Evitar -0.0
            if abs(holgura) < 1e-4:
                holgura = 0.0
            critica = holgura == 0.0
            subcritica = 0.0 < holgura <= 1.0

            tiempos[t_id] = TiemposCpm(
                early_start=es,
                early_finish=ef,
                late_start=ls,
                late_finish=lf,
                holgura_total=holgura,
            )
            es_critica_map[t_id] = critica
            es_subcritica_map[t_id] = subcritica

        # 4. Caminos críticos y subcríticos ordenados
        camino_critico = tuple(
            t_id for t_id in orden_topologico if es_critica_map[t_id]
        )
        camino_subcritico = tuple(
            t_id for t_id in orden_topologico if es_subcritica_map[t_id]
        )

        # 5. Estadísticas de incertidumbre (Varianza y Desviación estándar del camino crítico)
        varianza_total = round(
            sum(estimaciones[t_id].varianza for t_id in camino_critico), 4
        )
        desviacion_estandar = round(math.sqrt(varianza_total), 2)
        ic_min = max(0.0, round(duracion_proyecto - 1.645 * desviacion_estandar, 2))
        ic_max = round(duracion_proyecto + 1.645 * desviacion_estandar, 2)

        # 6. Construir tareas enriquecidas
        tareas_enriquecidas: list[TareaPlan] = []
        for t in tareas_raw:
            tareas_enriquecidas.append(
                TareaPlan(
                    id=t.id,
                    titulo=t.titulo,
                    descripcion=t.descripcion,
                    fase=t.fase,
                    estado=t.estado,
                    predecesores=t.predecesores,
                    estimacion=estimaciones[t.id],
                    tiempos=tiempos[t.id],
                    es_critica=es_critica_map[t.id],
                    es_subcritica=es_subcritica_map[t.id],
                    responsable=t.responsable,
                    metadatos=t.metadatos,
                )
            )

        # 7. Agrupación Kanban
        pendientes = tuple(
            t for t in tareas_enriquecidas if t.estado == EstadoTareaPlan.PENDIENTE
        )
        en_proceso = tuple(
            t for t in tareas_enriquecidas if t.estado == EstadoTareaPlan.EN_PROCESO
        )
        finalizadas = tuple(
            t for t in tareas_enriquecidas if t.estado == EstadoTareaPlan.COMPLETADA
        )

        total_tareas = len(tareas_enriquecidas)
        completadas = len(finalizadas)
        pct_avance = (
            round((completadas / total_tareas * 100.0), 1) if total_tareas > 0 else 0.0
        )

        metricas = MetricasProyecto(
            duracion_esperada=duracion_proyecto,
            varianza_total=varianza_total,
            desviacion_estandar=desviacion_estandar,
            intervalo_confianza_95_min=ic_min,
            intervalo_confianza_95_max=ic_max,
            camino_critico=camino_critico,
            camino_subcritico=camino_subcritico,
            total_tareas=total_tareas,
            tareas_pendientes=len(pendientes),
            tareas_en_proceso=len(en_proceso),
            tareas_completadas=completadas,
            porcentaje_avance=pct_avance,
        )

        diagrama_mermaid = cls._generar_diagrama_mermaid(tareas_enriquecidas)

        return TableroKanban(
            id_plan=id_plan,
            titulo_plan=titulo_plan,
            descripcion_plan=descripcion_plan,
            pendientes=pendientes,
            en_proceso=en_proceso,
            finalizadas=finalizadas,
            metricas=metricas,
            diagrama_mermaid=diagrama_mermaid,
        )

    @classmethod
    def _generar_diagrama_mermaid(cls, tareas: Sequence[TareaPlan]) -> str:
        """Genera dinámicamente el grafo Mermaid con estilos según estado y criticidad."""
        lines: list[str] = [
            "graph LR",
            "    classDef completed fill:#52c41a,stroke:#237804,stroke-width:2px,color:#fff;",
            "    classDef inprogress fill:#fa8c16,stroke:#ad4e00,stroke-width:2px,color:#fff;",
            "    classDef critical fill:#ff4d4f,stroke:#a8071a,stroke-width:2px,color:#fff;",
            "    classDef subcritical fill:#faad14,stroke:#d48806,stroke-width:2px,color:#000;",
            "    classDef normal fill:#f0f2f5,stroke:#8c8c8c,stroke-width:1px,color:#000;",
            "",
            "    START((Inicio))",
        ]

        # Nodos
        for t in tareas:
            clase = "normal"
            if t.estado == EstadoTareaPlan.COMPLETADA:
                clase = "completed"
            elif t.estado == EstadoTareaPlan.EN_PROCESO:
                clase = "inprogress"
            elif t.es_critica:
                clase = "critical"
            elif t.es_subcritica:
                clase = "subcritical"

            texto_nodo = f"{t.id}: {t.titulo}<br/>Te: {t.estimacion.esperada}d | H: {t.tiempos.holgura_total}d"
            lines.append(f'    {t.id}["{texto_nodo}"]:::{clase}')

        lines.append("")
        # Conexiones desde START
        for t in tareas:
            if not t.predecesores:
                lines.append(f"    START --> {t.id}")

        # Conexiones entre tareas
        for t in tareas:
            for pred in t.predecesores:
                lines.append(f"    {pred} --> {t.id}")

        return "\n".join(lines)
