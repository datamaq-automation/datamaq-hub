"""FastAPI routing para lectura de correos electrónicos vía IMAP (OpenClaw / Interno)."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.adapters.controllers.dependencies import get_mail_controller
from src.adapters.controllers.mail_controller import MailController
from src.adapters.gateways.imap_mail_gateway import ImapMailGateway
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.mail_dto import (
    EmailDetailDTO,
    EmailFolderDTO,
    MailInboxResponseDTO,
    UnreadSummaryDTO,
)
from src.infrastructure.pydantic.config import get_settings

router = APIRouter(prefix="/mail", tags=["Correo Electrónico (Mail Reader)"])


@lru_cache
def get_configured_mail_controller() -> MailController:
    """Proveedor de dependencias para MailController con configuración de entorno."""
    settings = get_settings()
    gateway = ImapMailGateway(
        host=settings.mail_imap_host,
        port=settings.mail_imap_port,
        user=settings.mail_imap_user,
        password=settings.mail_imap_pass,
        use_ssl=settings.mail_imap_use_ssl,
        timeout_seconds=settings.mail_imap_timeout_seconds,
    )
    return get_mail_controller(gateway=gateway)


@router.get(
    "/carpetas",
    response_model=APIResponseDTO[list[EmailFolderDTO]],
    summary="Listar Carpetas IMAP",
    description="Consulta y retorna todas las carpetas disponibles en el servidor con su conteo de mensajes totales y no leídos.",
)
async def list_folders(
    controller: Annotated[MailController, Depends(get_configured_mail_controller)],
) -> APIResponseDTO[list[EmailFolderDTO]]:
    """Obtiene la lista de carpetas IMAP."""
    folders = controller.get_folders()
    return APIResponseDTO[list[EmailFolderDTO]](
        success=True,
        data=folders,
    )


@router.get(
    "/inbox",
    response_model=APIResponseDTO[MailInboxResponseDTO],
    summary="Consultar Correos de la Bandeja de Entrada o Carpeta",
    description=(
        "Consulta y pagina los correos de la carpeta indicada en modo estricto de sólo lectura. "
        "Permite filtrar mensajes no leídos y ajustar el límite y desplazamiento."
    ),
)
async def list_inbox_messages(
    controller: Annotated[MailController, Depends(get_configured_mail_controller)],
    limit: int = Query(
        20, ge=1, le=100, description="Límite máximo de correos a retornar"
    ),
    desde: int = Query(0, ge=0, description="Desplazamiento / offset de paginación"),
    sin_leer: bool = Query(
        False, description="Filtrar exclusivamente correos no leídos"
    ),
    carpeta: str = Query("INBOX", description="Nombre de la carpeta IMAP a consultar"),
) -> APIResponseDTO[MailInboxResponseDTO]:
    """Retorna la lista paginada de correos."""
    result = controller.get_inbox_messages(
        folder=carpeta,
        limit=limit,
        offset=desde,
        sin_leer=sin_leer,
    )
    return APIResponseDTO[MailInboxResponseDTO](
        success=True,
        data=result,
    )


@router.get(
    "/inbox/sin-leer",
    response_model=APIResponseDTO[UnreadSummaryDTO],
    summary="Resumen Rápido de Correos No Leídos",
    description="Retorna el contador total de correos no leídos y una lista breve de los mensajes más recientes sin leer.",
)
async def get_unread_summary(
    controller: Annotated[MailController, Depends(get_configured_mail_controller)],
    limit: int = Query(
        5, ge=1, le=50, description="Cantidad máxima de no leídos recientes"
    ),
    carpeta: str = Query("INBOX", description="Nombre de la carpeta IMAP"),
) -> APIResponseDTO[UnreadSummaryDTO]:
    """Retorna el resumen de correos no leídos."""
    summary = controller.get_unread_summary(
        folder=carpeta,
        limit=limit,
    )
    return APIResponseDTO[UnreadSummaryDTO](
        success=True,
        data=summary,
    )


@router.get(
    "/inbox/{uid}",
    response_model=APIResponseDTO[EmailDetailDTO],
    summary="Obtener Detalle Completo de un Correo",
    description=(
        "Obtiene el detalle completo de un mensaje por su UID (asunto, remitente, destinatarios, "
        "cuerpo texto plano, cuerpo HTML y metadatos de adjuntos) sin alterar el flag de lectura en el servidor."
    ),
)
async def get_inbox_message_detail(
    uid: str,
    controller: Annotated[MailController, Depends(get_configured_mail_controller)],
    carpeta: str = Query("INBOX", description="Nombre de la carpeta IMAP"),
) -> APIResponseDTO[EmailDetailDTO]:
    """Retorna el detalle completo del correo."""
    detail = controller.get_message_detail(
        uid=uid,
        folder=carpeta,
    )
    return APIResponseDTO[EmailDetailDTO](
        success=True,
        data=detail,
    )


@router.get(
    "/{uid}",
    response_model=APIResponseDTO[EmailDetailDTO],
    summary="Obtener Detalle de Correo (Atajo por UID)",
    description="Atajo directo para consultar el detalle de un correo por su UID.",
)
async def get_message_detail_shortcut(
    uid: str,
    controller: Annotated[MailController, Depends(get_configured_mail_controller)],
    carpeta: str = Query("INBOX", description="Nombre de la carpeta IMAP"),
) -> APIResponseDTO[EmailDetailDTO]:
    """Retorna el detalle completo del correo por UID."""
    detail = controller.get_message_detail(
        uid=uid,
        folder=carpeta,
    )
    return APIResponseDTO[EmailDetailDTO](
        success=True,
        data=detail,
    )
