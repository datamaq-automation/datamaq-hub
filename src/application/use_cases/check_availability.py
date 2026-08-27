"""Use case for calculating schedule availability and free time slots."""

from datetime import date, datetime, time

from src.application.dtos.calendar_dto import AvailabilityResponseDTO
from src.application.mappers.calendar_mapper import CalendarMapper
from src.domain.calendar.ports import CalendarRepositoryPort
from src.domain.calendar.services import AvailabilityCheckerService


class CheckAvailabilityUseCase:
    """Use case to compute open appointment slots for a given day."""

    def __init__(self, repository: CalendarRepositoryPort) -> None:
        self.repository = repository

    def execute(
        self,
        account: str,
        target_date: date,
        slot_duration_minutes: int = 30,
        work_start_time: time = time(8, 0),
        work_end_time: time = time(18, 0),
    ) -> AvailabilityResponseDTO:
        day_start = datetime.combine(target_date, time(0, 0))
        day_end = datetime.combine(target_date, time(23, 59, 59))

        events = self.repository.list_events(
            account=account,
            start_date=day_start,
            end_date=day_end,
            limit=100,
        )

        slots = AvailabilityCheckerService.calculate_free_slots(
            target_date=target_date,
            events=events,
            work_start_time=work_start_time,
            work_end_time=work_end_time,
            slot_duration_minutes=slot_duration_minutes,
        )

        return AvailabilityResponseDTO(
            fecha=target_date.isoformat(),
            cuenta=account,
            duracion_minutos=slot_duration_minutes,
            bloques=[CalendarMapper.to_slot_dto(s) for s in slots],
        )
