"""FastAPI routes for calendar and scheduling."""

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from src.adapters.controllers.calendar_controller import CalendarController
from src.adapters.controllers.dependencies import get_calendar_controller
from src.application.dtos.calendar_docencia_dto import (
    SincronizacionDocenteResponseDTO,
    SincronizarDocenciaDTO,
)
from src.application.dtos.calendar_dto import (
    AvailabilityResponseDTO,
    CalendarEventCompactDTO,
    CalendarEventDTO,
    CreateEventDTO,
    UpdateEventDTO,
)
from src.application.dtos.common_dto import APIResponseDTO
from src.infrastructure.pydantic.config import get_settings

router = APIRouter(prefix="/calendario", tags=["Calendario"])


def get_configured_calendar_controller() -> CalendarController:
    """Dependency resolver creating CalendarController with configured DB."""
    settings = get_settings()
    from src.adapters.gateways.sql_calendar_gateway import SQLCalendarGateway
    from src.adapters.gateways.sql_designacion_docente_gateway import (
        SQLDesignacionDocenteGateway,
    )

    calendar_gw = SQLCalendarGateway(database_url=settings.roundcube_db_url)
    docencia_gw = SQLDesignacionDocenteGateway(database_url=settings.database_url)
    return get_calendar_controller(
        repository=calendar_gw, designacion_repository=docencia_gw
    )


def _proyectar_compacto(event: CalendarEventDTO) -> CalendarEventCompactDTO:
    """Reduce un evento a su representación de bajo-token (compact)."""
    return CalendarEventCompactDTO(
        id_evento=event.id_evento,
        titulo=event.titulo,
        inicio=event.inicio,
        fin=event.fin,
        estado=event.estado,
        cuenta=event.cuenta,
    )


@router.get(
    "/eventos",
    response_model=APIResponseDTO[list[CalendarEventDTO]]
    | APIResponseDTO[list[CalendarEventCompactDTO]],
)
async def list_events(
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    fecha_desde: Annotated[
        datetime | None,
        Query(description="Fecha y hora de inicio mínima (ISO 8601)"),
    ] = None,
    fecha_hasta: Annotated[
        datetime | None,
        Query(description="Fecha y hora de fin máxima (ISO 8601)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
    compact: Annotated[
        bool, Query(description="Proyectar solo campos esenciales (bajo-token)")
    ] = True,
) -> (
    APIResponseDTO[list[CalendarEventDTO]]
    | APIResponseDTO[list[CalendarEventCompactDTO]]
):
    """Lists calendar events within an optional date range."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    result = controller.list_events(
        account=effective_account,
        start_date=fecha_desde,
        end_date=fecha_hasta,
        limit=limit,
    )
    if compact:
        return APIResponseDTO[list[CalendarEventCompactDTO]](
            success=True, data=[_proyectar_compacto(e) for e in result]
        )
    return APIResponseDTO[list[CalendarEventDTO]](success=True, data=result)


@router.get("/proximos", response_model=APIResponseDTO[list[CalendarEventDTO]])
async def get_upcoming_events(
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    dias: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[list[CalendarEventDTO]]:
    """Retrieves forthcoming events for the next N days."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    result = controller.get_upcoming_events(
        account=effective_account, days=dias, limit=limit
    )
    return APIResponseDTO[list[CalendarEventDTO]](success=True, data=result)


@router.get("/disponibilidad", response_model=APIResponseDTO[AvailabilityResponseDTO])
async def check_availability(
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    fecha: Annotated[date, Query(description="Fecha a consultar (YYYY-MM-DD)")],
    duracion_minutos: Annotated[int, Query(ge=10, le=240)] = 30,
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[AvailabilityResponseDTO]:
    """Calculates open and busy time slots for a given date."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    result = controller.check_availability(
        account=effective_account,
        target_date=fecha,
        slot_duration_minutes=duracion_minutos,
    )
    return APIResponseDTO[AvailabilityResponseDTO](success=True, data=result)


@router.get("/eventos/{event_id}", response_model=APIResponseDTO[CalendarEventDTO])
async def get_event(
    event_id: str,
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[CalendarEventDTO]:
    """Retrieves full details of a calendar event."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    result = controller.get_event_detail(event_id=event_id, account=effective_account)
    return APIResponseDTO[CalendarEventDTO](success=True, data=result)


@router.post("/eventos", response_model=APIResponseDTO[CalendarEventDTO])
async def create_event(
    payload: CreateEventDTO,
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[CalendarEventDTO]:
    """Creates a new calendar event."""
    settings = get_settings()
    effective_account = payload.cuenta or account or settings.default_mail_account
    result = controller.create_event(dto=payload, account=effective_account)
    return APIResponseDTO[CalendarEventDTO](success=True, data=result)


@router.put("/eventos/{event_id}", response_model=APIResponseDTO[CalendarEventDTO])
async def update_event(
    event_id: str,
    payload: UpdateEventDTO,
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[CalendarEventDTO]:
    """Updates an existing calendar event."""
    settings = get_settings()
    effective_account = payload.cuenta or account or settings.default_mail_account
    result = controller.update_event(
        event_id=event_id, dto=payload, account=effective_account
    )
    return APIResponseDTO[CalendarEventDTO](success=True, data=result)


@router.delete("/eventos/{event_id}", response_model=APIResponseDTO[dict[str, Any]])
async def delete_event(
    event_id: str,
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[dict[str, Any]]:
    """Deletes an event from the calendar."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    deleted = controller.delete_event(event_id=event_id, account=effective_account)
    return APIResponseDTO[dict[str, Any]](
        success=True,
        data={"eliminado": deleted, "id_evento": event_id},
    )


@router.post(
    "/docencia/sincronizar",
    response_model=APIResponseDTO[SincronizacionDocenteResponseDTO],
    summary="Sincronizar Clases Docentes al Calendario",
    description="Proyecta las clases semanales de las designaciones docentes vigentes como eventos concretos en el calendario corporativo.",
)
async def sincronizar_docencia(
    payload: SincronizarDocenciaDTO,
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[SincronizacionDocenteResponseDTO]:
    """Projects and syncs teaching positions into calendar events."""
    settings = get_settings()
    effective_account = payload.account or account or settings.default_mail_account
    result = controller.sincronizar_docencia(dto=payload, account=effective_account)
    return APIResponseDTO[SincronizacionDocenteResponseDTO](success=True, data=result)


@router.get(
    "/docencia/agenda",
    response_model=APIResponseDTO[list[CalendarEventDTO]],
    summary="Consultar Agenda Unificada Docente",
    description="Obtiene la agenda consolidada de clases escolares y compromisos en un intervalo de fechas.",
)
async def consultar_agenda_docente(
    controller: Annotated[
        CalendarController, Depends(get_configured_calendar_controller)
    ],
    fecha_desde: Annotated[
        date, Query(description="Fecha inicial de consulta (YYYY-MM-DD)")
    ],
    fecha_hasta: Annotated[
        date, Query(description="Fecha final de consulta (YYYY-MM-DD)")
    ],
    solo_docencia: Annotated[
        bool,
        Query(description="Filtrar exclusivamente eventos de clases escolares"),
    ] = False,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=2000,
            description="Cantidad máxima de eventos a recuperar (por defecto 1000)",
        ),
    ] = 1000,
    account: Annotated[
        str | None,
        Query(
            description="Cuenta de correo asociada (opcional, por defecto openclaw@datamaq.com.ar)"
        ),
    ] = None,
) -> APIResponseDTO[list[CalendarEventDTO]]:
    """Retrieves unified teaching schedule."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    result = controller.consultar_agenda_docente(
        account=effective_account,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        solo_docencia=solo_docencia,
        limit=limit,
    )
    return APIResponseDTO[list[CalendarEventDTO]](success=True, data=result)
