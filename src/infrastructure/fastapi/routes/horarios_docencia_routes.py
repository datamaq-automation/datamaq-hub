"""FastAPI routing para horarios de docencia, compatibilidad y persistencia temporal."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.adapters.controllers.dependencies import get_horarios_docencia_controller
from src.adapters.controllers.horarios_docencia_controller import (
    HorariosDocenciaController,
)
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.horarios_docencia_dto import (
    CesarDesignacionInputDTO,
    DeclaracionHorariaInputDTO,
    DesignacionDocenteDTO,
    RegistrarDesignacionInputDTO,
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


@router.post(
    "/designaciones",
    response_model=APIResponseDTO[DesignacionDocenteDTO],
    summary="Registrar Designación o Suplencia Docente con Vigencia Temporal",
    description=(
        "Persiste una nueva designación, titularidad o suplencia de forma inmutable con su código IGE, "
        "rango de fechas (fecha_desde / fecha_hasta) y distribución horaria semanal."
    ),
)
async def registrar_designacion(
    input_dto: RegistrarDesignacionInputDTO,
    controller: Annotated[
        HorariosDocenciaController, Depends(get_horarios_docencia_controller)
    ],
) -> APIResponseDTO[DesignacionDocenteDTO]:
    """Registra y almacena la designación en base de datos."""
    guardada = controller.registrar_designacion(input_dto)
    return APIResponseDTO[DesignacionDocenteDTO](
        success=True,
        data=guardada,
    )


@router.post(
    "/designaciones/{id_designacion}/cesar",
    response_model=APIResponseDTO[DesignacionDocenteDTO],
    summary="Finalizar Vigencia de una Designación (Cese / Fin de Suplencia)",
    description=(
        "Registra la fecha de cese y el motivo (FIN_SUPLENCIA, RENUNCIA, etc.) de una designación "
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
