"""FastAPI routes for planificacion, Kanban board and PERT-CPM network."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.controllers.dependencies import get_planificacion_controller
from src.adapters.controllers.planificacion_controller import PlanificacionController
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.planificacion_dtos import (
    CambiarEstadoTareaPlanDTO,
    TableroKanbanDTO,
)

router = APIRouter(prefix="/planificacion", tags=["Planificación y Kanban PERT"])


@router.get(
    "/kanban",
    response_model=APIResponseDTO[TableroKanbanDTO],
    summary="Obtener tablero Kanban y análisis PERT-CPM",
    description=(
        "Devuelve las tareas agrupadas en columnas Kanban (pendientes, en_proceso, finalizadas), "
        "con sus holguras, tiempos CPM (ES, EF, LS, LF), camino crítico, subcrítico y diagrama Mermaid renderizable."
    ),
)
async def obtener_tablero_kanban(
    controller: Annotated[
        PlanificacionController, Depends(get_planificacion_controller)
    ],
    id_plan: Annotated[
        str, Query(description="Identificador del plan (por defecto 'vaca_muerta')")
    ] = "vaca_muerta",
) -> APIResponseDTO[TableroKanbanDTO]:
    """Consulta y calcula el tablero Kanban con análisis PERT-CPM."""
    tablero = controller.obtener_tablero(id_plan=id_plan)
    return APIResponseDTO(
        data=tablero,
    )


@router.patch(
    "/tareas/{id_tarea}/estado",
    response_model=APIResponseDTO[TableroKanbanDTO],
    summary="Actualizar estado de una tarea y recalcular tablero",
    description="Mueve una tarea de columna (PENDIENTE, EN_PROCESO, COMPLETADA) y recalcula la red PERT al instante.",
    status_code=status.HTTP_200_OK,
)
async def actualizar_estado_tarea(
    id_tarea: str,
    body: CambiarEstadoTareaPlanDTO,
    controller: Annotated[
        PlanificacionController, Depends(get_planificacion_controller)
    ],
    id_plan: Annotated[
        str, Query(description="Identificador del plan")
    ] = "vaca_muerta",
) -> APIResponseDTO[TableroKanbanDTO]:
    """Actualiza el estado de la tarea en el archivo de planificación y recalcula el tablero."""
    tablero = controller.actualizar_estado_tarea(
        id_tarea=id_tarea,
        nuevo_estado=body.estado,
        id_plan=id_plan,
    )
    return APIResponseDTO(
        data=tablero,
    )
