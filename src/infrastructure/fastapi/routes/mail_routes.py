"""FastAPI routing para lectura de correos electrónicos vía IMAP Multi-Cuenta (OpenClaw / Interno)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from src.adapters.controllers.dependencies import (
    get_mail_analysis_controller,
    get_mail_controller,
)
from src.adapters.controllers.mail_analysis_controller import MailAnalysisController
from src.adapters.controllers.mail_controller import MailController
from src.adapters.gateways.imap_mail_gateway import ImapMailGateway
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.mail_dto import (
    AnalisisEmailDTO,
    EmailDetailDTO,
    EmailFolderDTO,
    MailInboxResponseDTO,
    ScanMailRequestDTO,
    ScanMailResponseDTO,
    UnreadSummaryDTO,
)
from src.infrastructure.pydantic.config import get_settings

router = APIRouter(prefix="/mail", tags=["Correo Electrónico (Mail Reader)"])


def _build_mail_reader(account: str | None) -> tuple[Any, Any, str]:
    """Arma el lector de correo (Gmail o IMAP) con caché para la cuenta pedida.

    Devuelve `(reader_cacheado, cache, cuenta)`; la caché se reutiliza tanto para el
    decorador de lectura como para la deduplicación de alertas del analizador.
    """
    from src.adapters.gateways.api_cache_gateway import (
        ApiCacheGateway,
        resolve_database_url,
    )
    from src.adapters.gateways.cached_mail_reader_gateway import (
        CachedMailReaderGateway,
    )
    from src.adapters.gateways.gmail_api_gateway import GmailApiGateway
    from src.domain.mail.ports import MailReaderPort

    settings = get_settings()
    account_config = settings.get_mail_account_config(account)

    reader: MailReaderPort
    if account_config.oauth2_refresh_token:
        reader = GmailApiGateway(
            client_id=account_config.oauth2_client_id,
            client_secret=account_config.oauth2_client_secret,
            refresh_token=account_config.oauth2_refresh_token,
            user_email=account_config.user,
            timeout_seconds=account_config.timeout_seconds,
        )
    else:
        reader = ImapMailGateway(
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
    cache = ApiCacheGateway(
        database_url=resolve_database_url(settings.database_url),
        ttl_by_prefix=settings.cache_ttls or None,
    )
    gateway: MailReaderPort = CachedMailReaderGateway(
        reader=reader,
        cache=cache,
        account=account_config.user,
    )
    return gateway, cache, account_config.user


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
    gateway, _cache, _cuenta = _build_mail_reader(account)
    return get_mail_controller(gateway=gateway)


def get_configured_mail_analysis_controller(
    account: Annotated[
        str | None,
        Query(
            description="Identificador o email de la cuenta de correo (opcional, ej. 'datamaq', 'abc')",
            examples=["datamaq", "abc"],
        ),
    ] = None,
) -> MailAnalysisController:
    """Proveedor de dependencias para el analizador de oportunidades B2B en correo."""
    from src.adapters.controllers.dependencies import (
        get_default_contacts_gateway,
        get_default_mail_notifier_gateway,
        get_default_tarea_gateway,
    )

    settings = get_settings()
    gateway, cache, _cuenta = _build_mail_reader(account)
    return get_mail_analysis_controller(
        gateway=gateway,
        cache=cache,
        notifier=get_default_mail_notifier_gateway(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        ),
        contacts_repo=get_default_contacts_gateway(
            database_url=settings.roundcube_db_url
        ),
        tarea_repo=get_default_tarea_gateway(database_url=settings.database_url),
    )


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
        "Permite filtrar mensajes no leídos, buscar por texto (q) y ajustar el límite y desplazamiento."
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
    q: str | None = Query(
        None, description="Filtro o término de búsqueda (ej. 'SAD', 'designacion')"
    ),
    carpeta: str = Query("INBOX", description="Nombre de la carpeta IMAP a consultar"),
) -> APIResponseDTO[MailInboxResponseDTO]:
    """Retorna la lista paginada de correos con snippet de previsualización."""
    result = controller.get_inbox_messages(
        folder=carpeta,
        limit=limit,
        offset=desde,
        sin_leer=sin_leer,
        q=q,
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
    q: str | None = Query(None, description="Filtro o término de búsqueda (opcional)"),
    carpeta: str = Query("INBOX", description="Nombre de la carpeta IMAP"),
) -> APIResponseDTO[UnreadSummaryDTO]:
    """Retorna el resumen de correos no leídos."""
    summary = controller.get_unread_summary(
        folder=carpeta,
        limit=limit,
        q=q,
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
        "Obtiene el detalle de un mensaje por su UID (asunto, remitente, destinatarios, "
        "cuerpo texto plano y metadatos de adjuntos). Por defecto omite el HTML para ahorrar tokens."
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
    include_html: bool = Query(
        False,
        description="Incluir cuerpo HTML completo (por defecto False para ahorro de tokens)",
    ),
    max_chars: int = Query(
        4000,
        ge=100,
        le=100000,
        description="Límite máximo de caracteres en el cuerpo de texto",
    ),
) -> APIResponseDTO[EmailDetailDTO]:
    """Retorna el detalle optimizado del correo."""
    detail = controller.get_message_detail(
        uid=uid,
        folder=carpeta,
        include_html=include_html,
        max_chars=max_chars,
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
    include_html: bool = Query(
        False,
        description="Incluir cuerpo HTML completo (por defecto False para ahorro de tokens)",
    ),
    max_chars: int = Query(
        4000,
        ge=100,
        le=100000,
        description="Límite máximo de caracteres en el cuerpo de texto",
    ),
) -> APIResponseDTO[EmailDetailDTO]:
    """Retorna el detalle optimizado del correo por UID."""
    detail = controller.get_message_detail(
        uid=uid,
        folder=carpeta,
        include_html=include_html,
        max_chars=max_chars,
    )
    return APIResponseDTO[EmailDetailDTO](
        success=True,
        data=detail,
    )


@router.post(
    "/analizar",
    response_model=APIResponseDTO[ScanMailResponseDTO],
    summary="Escanear correos entrantes y alertar oportunidades B2B",
    description=(
        "Escanea los correos no leídos de la carpeta indicada con el motor determinístico "
        "de scoring, envía una alerta a Telegram por cada oportunidad comercial nueva "
        "(deduplicada 30 días) y opcionalmente registra el contacto y crea la tarea de "
        "respuesta. La lectura es estrictamente read-only: no altera el flag de leído."
    ),
)
def analizar_correos_endpoint(
    body: ScanMailRequestDTO,
    controller: Annotated[
        MailAnalysisController, Depends(get_configured_mail_analysis_controller)
    ],
) -> APIResponseDTO[ScanMailResponseDTO]:
    """Escanea el buzón y despacha alertas de oportunidad comercial."""
    resultado = controller.analizar_correos(dto=body)
    return APIResponseDTO[ScanMailResponseDTO](success=True, data=resultado)


@router.get(
    "/analizar/{uid}",
    response_model=APIResponseDTO[AnalisisEmailDTO],
    summary="Analizar un correo puntual",
    description=(
        "Devuelve el análisis de oportunidad de un correo por UID sin notificar ni "
        "escribir en la caché de deduplicación. Útil para inspeccionar el scoring."
    ),
)
def analizar_correo_endpoint(
    uid: str,
    controller: Annotated[
        MailAnalysisController, Depends(get_configured_mail_analysis_controller)
    ],
    cuenta: Annotated[str, Query(description="Cuenta de correo analizada")] = "datamaq",
    carpeta: Annotated[str, Query(description="Carpeta IMAP")] = "INBOX",
) -> APIResponseDTO[AnalisisEmailDTO]:
    """Analiza un correo individual sin efectos secundarios."""
    analisis = controller.analizar_correo(uid=uid, cuenta=cuenta, carpeta=carpeta)
    return APIResponseDTO[AnalisisEmailDTO](success=True, data=analisis)
