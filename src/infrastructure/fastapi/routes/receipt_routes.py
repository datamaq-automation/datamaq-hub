from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from src.adapters.controllers.dependencies import get_receipt_controller
from src.adapters.controllers.receipt_controller import ReceiptController
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.conciliacion_dto import ConciliacionResponseDTO
from src.application.dtos.horarios_docencia_dto import DesignacionDocenteDTO
from src.application.dtos.receipt_dto import ReceiptResponseDTO, ReceiptSummaryDTO

router = APIRouter(prefix="/recibos", tags=["Recibos"])


@router.post(
    "/parse",
    response_model=APIResponseDTO[ReceiptResponseDTO]
    | APIResponseDTO[ReceiptSummaryDTO],
    summary="Parsear e importar recibo de sueldo en PDF",
    description=(
        "Sube un recibo de sueldo en formato PDF (DGCyE PBA o genérico), extrae los datos estructurados "
        "y por defecto lo persiste en la base de datos para conciliación histórica."
    ),
    responses={
        200: {"description": "Recibo parseado y persistido con éxito"},
        400: {"description": "Archivo inválido o formato de PDF ilegible"},
        422: {"description": "Error en validación de esquema del documento"},
    },
)
async def parse_receipt(
    file: Annotated[UploadFile, File(description="Archivo PDF del recibo de sueldo")],
    controller: Annotated[ReceiptController, Depends(get_receipt_controller)],
    persistir: Annotated[
        bool, Query(description="True para almacenar el recibo en la base de datos")
    ] = True,
    solo_resumen: Annotated[
        bool, Query(description="Retornar solo el resumen reducido (bajo-token)")
    ] = False,
) -> APIResponseDTO[ReceiptResponseDTO] | APIResponseDTO[ReceiptSummaryDTO]:
    filename = file.filename or "receipt.pdf"

    if not filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file must be a PDF document.",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {e!s}",
        ) from e

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF file is empty.",
        )

    return controller.parse_bytes(
        content, filename=filename, persistir=persistir, solo_resumen=solo_resumen
    )


@router.get(
    "",
    response_model=APIResponseDTO[list[ReceiptResponseDTO]],
    summary="Listar recibos de sueldo persistidos",
    description="Obtiene la lista de recibos importados con filtros opcionales por CUIT y mes de pago.",
)
async def listar_recibos(
    controller: Annotated[ReceiptController, Depends(get_receipt_controller)],
    cuit: Annotated[str | None, Query(description="CUIT del docente a filtrar")] = None,
    mes_pago: Annotated[
        str | None, Query(description="Mes de pago a filtrar (YYYY-MM o YYYYMM)")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Cantidad máxima de resultados")
    ] = 50,
    offset: Annotated[int, Query(ge=0, description="Paginación offset")] = 0,
) -> APIResponseDTO[list[ReceiptResponseDTO]]:
    return controller.listar(cuit=cuit, mes_pago=mes_pago, limit=limit, offset=offset)


@router.get(
    "/{id_recibo}",
    response_model=APIResponseDTO[ReceiptResponseDTO],
    summary="Obtener detalle de un recibo de sueldo",
    description="Recupera la ficha completa y todas las líneas de liquidación de un recibo guardado.",
)
async def obtener_recibo(
    id_recibo: str,
    controller: Annotated[ReceiptController, Depends(get_receipt_controller)],
) -> APIResponseDTO[ReceiptResponseDTO]:
    return controller.obtener_por_id(id_recibo)


@router.delete(
    "/{id_recibo}",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Eliminar un recibo de sueldo",
    description="Elimina físicamente un recibo importado por su identificador único.",
)
async def eliminar_recibo(
    id_recibo: str,
    controller: Annotated[ReceiptController, Depends(get_receipt_controller)],
) -> APIResponseDTO[dict[str, Any]]:
    return controller.eliminar(id_recibo)


@router.get(
    "/{id_recibo}/conciliacion",
    response_model=APIResponseDTO[ConciliacionResponseDTO],
    summary="Conciliar recibo vs designaciones docentes (Reporte Liquidado vs Esperado)",
    description=(
        "Cruza cada línea liquidada en el recibo (incluyendo suplencias retroactivas cesadas) "
        "frente al historial de designaciones del docente. Identifica cargos conciliados, discrepancias "
        "y líneas huérfanas sin respaldo."
    ),
)
async def conciliar_recibo(
    id_recibo: str,
    controller: Annotated[ReceiptController, Depends(get_receipt_controller)],
) -> APIResponseDTO[ConciliacionResponseDTO]:
    return controller.conciliar(id_recibo)


@router.post(
    "/{id_recibo}/crear-designaciones-huerfanas",
    response_model=APIResponseDTO[list[DesignacionDocenteDTO]],
    summary="Auto-crear designaciones desde líneas huérfanas del recibo",
    description=(
        "Genera y persiste automáticamente designaciones históricas para aquellas líneas del recibo "
        "que no contaban con cargo registrado en el sistema."
    ),
)
async def crear_designaciones_huerfanas(
    id_recibo: str,
    controller: Annotated[ReceiptController, Depends(get_receipt_controller)],
    secuencias: Annotated[
        list[str] | None,
        Query(description="Opcional: lista de secuencias específicas a crear"),
    ] = None,
) -> APIResponseDTO[list[DesignacionDocenteDTO]]:
    return controller.crear_designaciones_huerfanas(
        id_recibo=id_recibo, secuencias=secuencias
    )
