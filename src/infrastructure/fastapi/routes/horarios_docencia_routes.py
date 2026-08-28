"""FastAPI routing para horarios de docencia, compatibilidad y persistencia temporal."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.adapters.controllers.dependencies import get_horarios_docencia_controller
from src.adapters.controllers.horarios_docencia_controller import (
    HorariosDocenciaController,
)
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.horarios_docencia_dto import (
    ActualizarDesignacionInputDTO,
    CesarDesignacionInputDTO,
    DeclaracionHorariaInputDTO,
    DesignacionDocenteDTO,
    RegistrarDesignacionInputDTO,
    RegistrarDesignacionResponseDTO,
    ResultadoCompatibilidadDTO,
)

router = APIRouter(
    prefix="/horarios-docencia", tags=["Horarios y Compatibilidad Docente"]
)


@router.post(
    "/validar",
    response_model=APIResponseDTO[ResultadoCompatibilidadDTO],
    summary="Auditar y Validar Compatibilidad Horaria Ad-hoc",
    description=(
        "Analiza una declaración jurada de cargos y horarios escolares enviada en el payload. "
        "Detecta superposiciones horarias exactas, valida márgenes de traslado entre escuelas, "
        "comprueba topes estatutarios (módulos y cargos base) y genera la grilla semanal estructurada."
    ),
)
async def validar_declaracion_horaria(
    input_dto: DeclaracionHorariaInputDTO,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
) -> APIResponseDTO[ResultadoCompatibilidadDTO]:
    """Ejecuta la auditoría y retorna el reporte de compatibilidad."""
    resultado = controller.validar_declaracion(input_dto)
    return APIResponseDTO[ResultadoCompatibilidadDTO](
        success=True,
        data=resultado,
    )


@router.get(
    "/designaciones",
    response_model=APIResponseDTO[list[DesignacionDocenteDTO]],
    summary="Listar Designaciones Docentes con Filtros y Paginación",
    description="Permite listar y auditar todas las designaciones cargadas, filtrando opcionalmente por CUIT, fecha de vigencia, establecimiento o distrito.",
)
async def listar_designaciones(
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
    cuit: str | None = Query(default=None, description="Filtrar por CUIT del docente"),
    vigentes_al: str | None = Query(
        default=None,
        description="Filtrar designaciones activas en una fecha (YYYY-MM-DD)",
    ),
    establecimiento: str | None = Query(
        default=None, description="Filtrar por nombre o fragmento de escuela"
    ),
    distrito: str | None = Query(
        default=None, description="Filtrar por distrito escolar"
    ),
    limit: int = Query(default=100, ge=1, le=500, description="Límite de registros"),
    offset: int = Query(default=0, ge=0, description="Desplazamiento para paginación"),
) -> APIResponseDTO[list[DesignacionDocenteDTO]]:
    """Retorna la lista de designaciones según filtros."""
    resultados = controller.listar_designaciones(
        cuit=cuit,
        vigentes_al_str=vigentes_al,
        establecimiento=establecimiento,
        distrito=distrito,
        limit=limit,
        offset=offset,
    )
    return APIResponseDTO[list[DesignacionDocenteDTO]](
        success=True,
        data=resultados,
    )


@router.get(
    "/designaciones/{id_designacion}",
    response_model=APIResponseDTO[DesignacionDocenteDTO],
    summary="Obtener Ficha Detallada de una Designación",
    description="Recupera la ficha completa de una designación docente por su ID único.",
)
async def obtener_designacion(
    id_designacion: str,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
) -> APIResponseDTO[DesignacionDocenteDTO]:
    """Obtiene una designación por ID."""
    desig = controller.obtener_designacion_por_id(id_designacion)
    if not desig:
        raise HTTPException(
            status_code=404,
            detail=f"Designación con ID '{id_designacion}' no encontrada.",
        )
    return APIResponseDTO[DesignacionDocenteDTO](
        success=True,
        data=desig,
    )


@router.post(
    "/designaciones",
    response_model=APIResponseDTO[RegistrarDesignacionResponseDTO],
    summary="Registrar Designación o Suplencia Docente con Vigencia Temporal",
    description=(
        "Persiste una nueva designación, titularidad o suplencia de forma inmutable con su código IGE, "
        "rango de fechas (fecha_desde / fecha_hasta), campos administrativos DGCyE y distribución horaria semanal. "
        "Audita en tiempo real posibles superposiciones con otros cargos vigentes del docente."
    ),
)
async def registrar_designacion(
    input_dto: RegistrarDesignacionInputDTO,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
) -> APIResponseDTO[RegistrarDesignacionResponseDTO]:
    """Registra y almacena la designación en base de datos retornando auditoría de compatibilidad."""
    guardada = controller.registrar_designacion(input_dto)
    return APIResponseDTO[RegistrarDesignacionResponseDTO](
        success=True,
        data=guardada,
    )


@router.put(
    "/designaciones/{id_designacion}",
    response_model=APIResponseDTO[DesignacionDocenteDTO],
    summary="Actualizar Integralmente una Designación",
    description="Permite corregir cualquier dato de la designación (fechas, materias, escuelas, horarios, observaciones).",
)
@router.patch(
    "/designaciones/{id_designacion}",
    response_model=APIResponseDTO[DesignacionDocenteDTO],
    summary="Modificar Parcialmente una Designación",
    description="Permite modificar campos específicos de la designación existente.",
)
async def actualizar_designacion(
    id_designacion: str,
    input_dto: ActualizarDesignacionInputDTO,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
) -> APIResponseDTO[DesignacionDocenteDTO]:
    """Actualiza una designación por ID."""
    actualizada = controller.actualizar_designacion(id_designacion, input_dto)
    if not actualizada:
        raise HTTPException(
            status_code=404,
            detail=f"Designación con ID '{id_designacion}' no encontrada para actualizar.",
        )
    return APIResponseDTO[DesignacionDocenteDTO](
        success=True,
        data=actualizada,
    )


@router.delete(
    "/designaciones/{id_designacion}",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Eliminar Físicamente una Designación",
    description="Elimina de forma permanente una designación cargada por error (distinto al cese administrativo).",
)
async def eliminar_designacion(
    id_designacion: str,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
) -> APIResponseDTO[dict[str, Any]]:
    """Elimina físicamente una designación."""
    eliminada = controller.eliminar_designacion(id_designacion)
    if not eliminada:
        raise HTTPException(
            status_code=404,
            detail=f"Designación con ID '{id_designacion}' no encontrada para eliminar.",
        )
    return APIResponseDTO[dict[str, Any]](
        success=True,
        data={"eliminado": True, "id_designacion": id_designacion},
    )


@router.post(
    "/designaciones/{id_designacion}/cesar",
    response_model=APIResponseDTO[DesignacionDocenteDTO],
    summary="Finalizar Vigencia de una Designación (Cese / Fin de Suplencia)",
    description=(
        "Registra la fecha de cese y el motivo (FIN_SUPLENCIA, REINCORPORACION_TITULAR, FIN_LICENCIA, RENUNCIA, etc.) de una designación "
        "existente sin borrarla de la base de datos."
    ),
)
async def cesar_designacion(
    id_designacion: str,
    input_dto: CesarDesignacionInputDTO,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
) -> APIResponseDTO[DesignacionDocenteDTO]:
    """Sella la vigencia de la designación."""
    actualizada = controller.cesar_designacion(id_designacion, input_dto)
    if not actualizada:
        raise HTTPException(
            status_code=404,
            detail=f"Designación con ID '{id_designacion}' no encontrada.",
        )
    return APIResponseDTO[DesignacionDocenteDTO](
        success=True,
        data=actualizada,
    )


@router.get(
    "/docentes/{cuit}/vigentes",
    response_model=APIResponseDTO[ResultadoCompatibilidadDTO],
    summary="Consultar y Auditar Cargos Vigentes de un Docente en una Fecha",
    description=(
        "Recupera de la base de datos todos los cargos que estaban activos en la fecha indicada "
        "(o en la fecha actual por defecto) y audita su compatibilidad horaria."
    ),
)
async def consultar_vigentes_docente(
    cuit: str,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
    fecha: str | None = Query(
        default=None,
        description="Fecha a evaluar en formato YYYY-MM-DD (ej. '2026-08-27'). Por defecto evalúa hoy.",
    ),
    margen_traslado: int = Query(
        default=20,
        ge=0,
        le=120,
        description="Minutos mínimos de traslado requeridos entre escuelas distintas.",
    ),
) -> APIResponseDTO[ResultadoCompatibilidadDTO]:
    """Retorna los cargos activos y su veredicto de compatibilidad."""
    resultado = controller.consultar_vigentes_en_fecha(
        docente_cuit=cuit,
        fecha_str=fecha,
        margen_traslado_minutos=margen_traslado,
    )
    return APIResponseDTO[ResultadoCompatibilidadDTO](
        success=True,
        data=resultado,
    )


@router.get(
    "/docentes/{cuit}/historial",
    response_model=APIResponseDTO[list[DesignacionDocenteDTO]],
    summary="Consultar Historial Completo y Línea de Tiempo de un Docente",
    description=(
        "Retorna la cronología inmutable completa de todas las designaciones, suplencias y cargos "
        "que el docente tuvo registradas en el sistema."
    ),
)
async def consultar_historial_docente(
    cuit: str,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
) -> APIResponseDTO[list[DesignacionDocenteDTO]]:
    """Retorna la lista histórica completa ordenada cronológicamente."""
    historial = controller.consultar_historial(docente_cuit=cuit)
    return APIResponseDTO[list[DesignacionDocenteDTO]](
        success=True,
        data=historial,
    )
