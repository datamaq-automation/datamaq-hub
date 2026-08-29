"""FastAPI routing para lectura de correos electrónicos vía IMAP Multi-Cuenta (OpenClaw / Interno)."""

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


def get_configured_mail_controller(
    account: Annotated[
        str | None,
        Query(
            description="Identificador o email de la cuenta de correo (opcional, ej. 'datamaq', 'abc')",
            examples=["datamaq", "abc"],
        ),
    ] = None,
) -> MailController:
    """Proveedor de dependencias para MailController configurado según la cuenta solicitada."""
    from src.adapters.gateways.gmail_api_gateway import GmailApiGateway
    from src.domain.mail.ports import MailReaderPort

    settings = get_settings()
    account_config = settings.get_mail_account_config(account)

    gateway: MailReaderPort
    if account_config.oauth2_refresh_token:
        gateway = GmailApiGateway(
            client_id=account_config.oauth2_client_id,
            client_secret=account_config.oauth2_client_secret,
            refresh_token=account_config.oauth2_refresh_token,
            user_email=account_config.user,
            timeout_seconds=account_config.timeout_seconds,
        )
    else:
        gateway = ImapMailGateway(
            host=account_config.host,
            port=account_config.port,
            user=account_config.user,
            password=account_config.password,
            use_ssl=account_config.use_ssl,
            timeout_seconds=account_config.timeout_seconds,
            oauth2_client_id=account_config.oauth2_client_id,
            oauth2_client_secret=account_config.oauth2_client_secret,
            oauth2_refresh_token=account_config.oauth2_refresh_token,
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
    account: Annotated[
        str | None,
        Query(description="Identificador o email de la cuenta de correo (opcional)"),
    ] = None,
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
    account: Annotated[
        str | None,
        Query(description="Identificador o email de la cuenta de correo (opcional)"),
    ] = None,
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
    account: Annotated[
        str | None,
        Query(description="Identificador o email de la cuenta de correo (opcional)"),
    ] = None,
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
    account: Annotated[
        str | None,
        Query(description="Identificador o email de la cuenta de correo (opcional)"),
    ] = None,
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
    account: Annotated[
        str | None,
        Query(description="Identificador o email de la cuenta de correo (opcional)"),
    ] = None,
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
