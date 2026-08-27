"""Use case for projecting and synchronizing teaching positions into calendar events."""

from datetime import datetime, time

from src.application.dtos.calendar_docencia_dto import (
    SincronizacionDocenteResponseDTO,
    SincronizarDocenciaDTO,
)
from src.application.mappers.calendar_mapper import CalendarMapper
from src.domain.calendar.ports import CalendarRepositoryPort
from src.domain.calendar.services import DocenciaEventProjectorService
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.ports import (
    DesignacionDocenteRepositoryPort,
)


class SincronizarAgendaDocenteUseCase:
    """Use case to synchronize weekly teaching blocks as concrete calendar events."""

    def __init__(
        self,
        designacion_repo: DesignacionDocenteRepositoryPort,
        calendar_repo: CalendarRepositoryPort,
    ) -> None:
        self.designacion_repo = designacion_repo
        self.calendar_repo = calendar_repo

    def execute(
        self, dto: SincronizarDocenciaDTO, account: str
    ) -> SincronizacionDocenteResponseDTO:
        effective_account = dto.account or account
        calendar = self.calendar_repo.get_or_create_default_calendar(
            account=effective_account
        )

        # 1. Fetch teaching positions for this CUIT
        historial: tuple[DesignacionDocente, ...] = (
            self.designacion_repo.obtener_historial(docente_cuit=dto.cuit)
        )
        active_desigs = [
            d
            for d in historial
            if not (d.vigencia.fecha_hasta and d.vigencia.fecha_hasta < dto.fecha_desde)
            and d.vigencia.fecha_desde <= dto.fecha_hasta
        ]

        # 2. Clean previous docencia events if requested
        if dto.limpiar_previos:
            dt_from = datetime.combine(dto.fecha_desde, time(0, 0))
            dt_to = datetime.combine(dto.fecha_hasta, time(23, 59, 59))
            existing_events = self.calendar_repo.list_events(
                account=effective_account,
                start_date=dt_from,
                end_date=dt_to,
                limit=500,
            )
            for ev in existing_events:
                if "docencia" in ev.categorias.lower() or ev.uid.startswith("doc-"):
                    self.calendar_repo.delete_event(
                        event_id=ev.id_evento, account=effective_account
                    )

        # 3. Project teaching schedule into concrete events
        projected = DocenciaEventProjectorService.project_events(
            designaciones=active_desigs,
            fecha_desde=dto.fecha_desde,
            fecha_hasta=dto.fecha_hasta,
            calendar_id=calendar.id_calendario,
            account=effective_account,
        )

        # 4. Persist projected events
        saved_dtos = []
        for ev in projected:
            created = self.calendar_repo.create_event(
                event=ev, account=effective_account
            )
            saved_dtos.append(CalendarMapper.to_event_dto(created))

        return SincronizacionDocenteResponseDTO(
            cuit=dto.cuit,
            cuenta=effective_account,
            fecha_desde=dto.fecha_desde,
            fecha_hasta=dto.fecha_hasta,
            total_eventos_creados=len(saved_dtos),
            eventos=saved_dtos,
        )
