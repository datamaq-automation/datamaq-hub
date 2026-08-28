"""Rutas FastAPI para el subdominio de tareas (To-Do List)."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.adapters.controllers.dependencies import get_tarea_controller
from src.adapters.controllers.tarea_controller import TareaController
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.tarea_dtos import (
    ActualizarTareaDTO,
    CrearTareaDTO,
    GenerarTareasReciboResponseDTO,
    ListarTareasResponseDTO,
    TareaResponseDTO,
)
from src.domain.recibos.exceptions import ReciboNotFoundError
from src.domain.tareas.exceptions import (
    TareaInvalidaException,
    TareaNoEncontradaException,
)
from src.domain.tareas.ports import FiltrosTarea
from src.domain.tareas.value_objects import (
    CategoriaTarea,
    EstadoTarea,
    PrioridadTarea,
)

router = APIRouter(prefix="/tareas", tags=["Tareas"])


@router.post(
    "",
    response_model=APIResponseDTO[TareaResponseDTO],
    summary="Crear una nueva tarea o pendiente",
    status_code=status.HTTP_201_CREATED,
)
def crear_tarea(
    dto: CrearTareaDTO,
    controller: Annotated[TareaController, Depends(get_tarea_controller)],
) -> APIResponseDTO[TareaResponseDTO]:
    try:
        return controller.crear(dto)
    except TareaInvalidaException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "",
    response_model=APIResponseDTO[ListarTareasResponseDTO],
    summary="Listar tareas con filtros opcionales",
)
def listar_tareas(
    controller: Annotated[TareaController, Depends(get_tarea_controller)],
    estado: Annotated[
        EstadoTarea | None, Query(description="Filtrar por estado")
    ] = None,
    categoria: Annotated[
        CategoriaTarea | None, Query(description="Filtrar por categoría")
    ] = None,
    prioridad: Annotated[
        PrioridadTarea | None, Query(description="Filtrar por prioridad")
    ] = None,
    cuit: Annotated[str | None, Query(description="Filtrar por CUIT docente")] = None,
    id_referencia: Annotated[
        str | None, Query(description="Filtrar por ID de referencia (ej. id_recibo)")
    ] = None,
    fecha_desde: Annotated[
        date | None, Query(description="Fecha límite desde (YYYY-MM-DD)")
    ] = None,
    fecha_hasta: Annotated[
        date | None, Query(description="Fecha límite hasta (YYYY-MM-DD)")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Límite de resultados")] = 50,
    offset: Annotated[int, Query(ge=0, description="Desplazamiento")] = 0,
) -> APIResponseDTO[ListarTareasResponseDTO]:
    filtros = FiltrosTarea(
        estado=estado,
        categoria=categoria,
        prioridad=prioridad,
        docente_cuit=cuit,
        id_referencia=id_referencia,
        fecha_limite_desde=fecha_desde,
        fecha_limite_hasta=fecha_hasta,
        limite=limit,
        offset=offset,
    )
    return controller.listar(filtros)


@router.get(
    "/{id_tarea}",
    response_model=APIResponseDTO[TareaResponseDTO],
    summary="Obtener detalle de una tarea por su ID",
)
def obtener_tarea(
    id_tarea: str,
    controller: Annotated[TareaController, Depends(get_tarea_controller)],
) -> APIResponseDTO[TareaResponseDTO]:
    try:
        return controller.obtener_por_id(id_tarea)
    except TareaNoEncontradaException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.patch(
    "/{id_tarea}",
    response_model=APIResponseDTO[TareaResponseDTO],
    summary="Actualizar campos de una tarea",
)
def actualizar_tarea(
    id_tarea: str,
    dto: ActualizarTareaDTO,
    controller: Annotated[TareaController, Depends(get_tarea_controller)],
) -> APIResponseDTO[TareaResponseDTO]:
    try:
        return controller.actualizar(id_tarea, dto)
    except TareaNoEncontradaException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except TareaInvalidaException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{id_tarea}/completar",
    response_model=APIResponseDTO[TareaResponseDTO],
    summary="Marcar tarea como completada",
)
def completar_tarea(
    id_tarea: str,
    controller: Annotated[TareaController, Depends(get_tarea_controller)],
) -> APIResponseDTO[TareaResponseDTO]:
    try:
        return controller.completar(id_tarea)
    except TareaNoEncontradaException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete(
    "/{id_tarea}",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Eliminar una tarea",
)
def eliminar_tarea(
    id_tarea: str,
    controller: Annotated[TareaController, Depends(get_tarea_controller)],
) -> APIResponseDTO[dict[str, Any]]:
    try:
        return controller.eliminar(id_tarea)
    except TareaNoEncontradaException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/generar-desde-recibo/{id_recibo}",
    response_model=APIResponseDTO[GenerarTareasReciboResponseDTO],
    summary="Auto-generar tareas a partir de la conciliación de un recibo",
    description="Detecta cargos no cobrados o discrepancias en la conciliación del recibo y crea tareas pendientes con prioridad alta.",
)
def generar_tareas_desde_recibo(
    id_recibo: str,
    controller: Annotated[TareaController, Depends(get_tarea_controller)],
) -> APIResponseDTO[GenerarTareasReciboResponseDTO]:
    try:
        return controller.generar_desde_recibo(id_recibo)
    except ReciboNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
