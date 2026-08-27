"""FastAPI routing para validación de horarios y compatibilidad docente."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.adapters.controllers.dependencies import get_horarios_docencia_controller
from src.adapters.controllers.horarios_docencia_controller import (
    HorariosDocenciaController,
)
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.horarios_docencia_dto import (
    DeclaracionHorariaInputDTO,
    ResultadoCompatibilidadDTO,
)

router = APIRouter(
    prefix="/horarios-docencia", tags=["Horarios y Compatibilidad Docente"]
)


@router.post(
    "/validar",
    response_model=APIResponseDTO[ResultadoCompatibilidadDTO],
    summary="Auditar y Validar Compatibilidad Horaria Docente",
    description=(
        "Analiza una declaración jurada de cargos y horarios escolares. "
        "Detecta superposiciones horarias exactas, valida márgenes de traslado entre escuelas, "
        "comprueba topes estatutarios (módulos y cargos base) y genera la grilla semanal estructurada."
    ),
    responses={
        200: {"description": "Declaración horaria auditada con éxito"},
        422: {"description": "Datos de entrada inválidos o formato horario incorrecto"},
    },
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
