"""Rutas HTTP para la carga de resúmenes de tarjetas de crédito."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from src.adapters.controllers.dependencies import get_tarjeta_controller
from src.adapters.controllers.tarjeta_controller import TarjetaController
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.tarjeta_dto import ResumenTarjetaDTO

router = APIRouter(prefix="/tarjetas", tags=["Tarjetas"])


@router.post(
    "/cargar",
    response_model=APIResponseDTO[ResumenTarjetaDTO],
    summary="Cargar y procesar un resumen de tarjeta de crédito en PDF",
    description=(
        "Sube un resumen de tarjeta de crédito (BBVA o Banco Provincia), "
        "extrae sus datos y lo persiste para el briefing de finanzas personales."
    ),
    responses={
        200: {"description": "Resumen parseado y persistido con éxito"},
        422: {"description": "Formato de PDF de tarjeta no reconocido o ilegible"},
    },
)
async def cargar_resumen(
    file: Annotated[UploadFile, File(description="Archivo PDF del resumen de tarjeta")],
    controller: Annotated[TarjetaController, Depends(get_tarjeta_controller)],
) -> APIResponseDTO[ResumenTarjetaDTO]:
    content = await file.read()
    return controller.cargar_resumen(content)
