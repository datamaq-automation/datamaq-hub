"""Dependency injection providers for controllers and use cases."""

from functools import lru_cache

from src.adapters.controllers.health_controller import HealthController
from src.adapters.controllers.horarios_docencia_controller import (
    HorariosDocenciaController,
)
from src.adapters.controllers.mail_controller import MailController
from src.adapters.controllers.receipt_controller import ReceiptController
from src.adapters.controllers.simulation_controller import SimulationController
from src.adapters.gateways.imap_mail_gateway import ImapMailGateway
from src.adapters.gateways.paritaria_json_gateway import ParitariaJsonGateway
from src.adapters.gateways.pdfplumber_extractor_gateway import (
    PdfPlumberExtractorGateway,
)
from src.adapters.gateways.receipt_parsers.parser_registry_gateway import (
    ReceiptParserRegistryGateway,
)
from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.application.use_cases.cesar_designacion import CesarDesignacionUseCase
from src.application.use_cases.consultar_designaciones_vigentes import (
    ConsultarDesignacionesVigentesUseCase,
)
from src.application.use_cases.consultar_historial_docente import (
    ConsultarHistorialDocenteUseCase,
)
from src.application.use_cases.get_mail_detail import GetMailDetailUseCase
from src.application.use_cases.get_unread_summary import GetUnreadSummaryUseCase
from src.application.use_cases.list_inbox_messages import ListInboxMessagesUseCase
from src.application.use_cases.list_mail_folders import ListMailFoldersUseCase
from src.application.use_cases.parse_receipt import ParseReceiptUseCase
from src.application.use_cases.project_salary import ProjectSalaryUseCase
from src.application.use_cases.registrar_designacion import (
    RegistrarDesignacionUseCase,
)
from src.application.use_cases.validar_horarios_docencia import (
    ValidarHorariosDocenciaUseCase,
)
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.liquidacion.ports import ParitariaRepositoryPort
from src.domain.liquidacion.services import MotorLiquidacionDocenteService
from src.domain.mail.ports import MailReaderPort
from src.domain.recibos.ports import PDFExtractorPort, ReceiptParserRegistryPort


@lru_cache
def get_pdf_extractor_gateway() -> PDFExtractorPort:
    return PdfPlumberExtractorGateway()


@lru_cache
def get_parser_registry_gateway() -> ReceiptParserRegistryPort:
    return ReceiptParserRegistryGateway()


def get_parse_receipt_use_case() -> ParseReceiptUseCase:
    extractor = get_pdf_extractor_gateway()
    parser_registry = get_parser_registry_gateway()
    return ParseReceiptUseCase(extractor=extractor, parser_registry=parser_registry)


@lru_cache
def get_motor_liquidacion_service() -> MotorLiquidacionDocenteService:
    return MotorLiquidacionDocenteService()


@lru_cache
def get_paritaria_repository_gateway() -> ParitariaRepositoryPort:
    return ParitariaJsonGateway()


def get_project_salary_use_case() -> ProjectSalaryUseCase:
    motor = get_motor_liquidacion_service()
    paritaria_repo = get_paritaria_repository_gateway()
    return ProjectSalaryUseCase(paritaria_repo=paritaria_repo, motor=motor)


@lru_cache
def get_designacion_docente_repository_gateway() -> DesignacionDocenteRepositoryPort:
    return SQLDesignacionDocenteGateway()


def get_health_controller() -> HealthController:
    return HealthController()


def get_receipt_controller() -> ReceiptController:
    use_case = get_parse_receipt_use_case()
    return ReceiptController(parse_use_case=use_case)


def get_simulation_controller() -> SimulationController:
    use_case = get_project_salary_use_case()
    return SimulationController(project_use_case=use_case)


def get_validar_horarios_use_case() -> ValidarHorariosDocenciaUseCase:
    return ValidarHorariosDocenciaUseCase()


def get_registrar_designacion_use_case() -> RegistrarDesignacionUseCase:
    repo = get_designacion_docente_repository_gateway()
    return RegistrarDesignacionUseCase(repository=repo)


def get_cesar_designacion_use_case() -> CesarDesignacionUseCase:
    repo = get_designacion_docente_repository_gateway()
    return CesarDesignacionUseCase(repository=repo)


def get_consultar_vigentes_use_case() -> ConsultarDesignacionesVigentesUseCase:
    repo = get_designacion_docente_repository_gateway()
    return ConsultarDesignacionesVigentesUseCase(repository=repo)


def get_consultar_historial_use_case() -> ConsultarHistorialDocenteUseCase:
    repo = get_designacion_docente_repository_gateway()
    return ConsultarHistorialDocenteUseCase(repository=repo)


def get_horarios_docencia_controller() -> HorariosDocenciaController:
    validar_uc = get_validar_horarios_use_case()
    registrar_uc = get_registrar_designacion_use_case()
    cesar_uc = get_cesar_designacion_use_case()
    vigentes_uc = get_consultar_vigentes_use_case()
    historial_uc = get_consultar_historial_use_case()
    return HorariosDocenciaController(
        validar_use_case=validar_uc,
        registrar_use_case=registrar_uc,
        cesar_use_case=cesar_uc,
        consultar_vigentes_use_case=vigentes_uc,
        consultar_historial_use_case=historial_uc,
    )


from src.adapters.controllers.calendar_controller import CalendarController
from src.adapters.controllers.contacts_controller import ContactsController
from src.adapters.gateways.sql_calendar_gateway import SQLCalendarGateway
from src.adapters.gateways.sql_contacts_gateway import SQLContactsGateway
from src.application.use_cases.check_availability import CheckAvailabilityUseCase
from src.application.use_cases.create_calendar_event import (
    CreateCalendarEventUseCase,
)
from src.application.use_cases.create_contact import CreateContactUseCase
from src.application.use_cases.delete_calendar_event import (
    DeleteCalendarEventUseCase,
)
from src.application.use_cases.delete_contact import DeleteContactUseCase
from src.application.use_cases.get_contact_detail import GetContactDetailUseCase
from src.application.use_cases.get_event_detail import GetEventDetailUseCase
from src.application.use_cases.get_upcoming_events import (
    GetUpcomingEventsUseCase,
)
from src.application.use_cases.list_calendar_events import (
    ListCalendarEventsUseCase,
)
from src.application.use_cases.list_contacts import ListContactsUseCase
from src.application.use_cases.update_calendar_event import (
    UpdateCalendarEventUseCase,
)
from src.application.use_cases.update_contact import UpdateContactUseCase
from src.domain.calendar.ports import CalendarRepositoryPort
from src.domain.contacts.ports import ContactsRepositoryPort


def get_default_mail_reader_gateway() -> MailReaderPort:
    """Creates a default ImapMailGateway instance."""
    return ImapMailGateway()


def get_mail_controller(
    gateway: MailReaderPort | None = None,
) -> MailController:
    """Builds and returns a MailController instance."""
    reader = gateway or get_default_mail_reader_gateway()
    list_folders_uc = ListMailFoldersUseCase(mail_reader=reader)
    list_inbox_uc = ListInboxMessagesUseCase(mail_reader=reader)
    get_detail_uc = GetMailDetailUseCase(mail_reader=reader)
    get_unread_uc = GetUnreadSummaryUseCase(mail_reader=reader)
    return MailController(
        list_folders_use_case=list_folders_uc,
        list_inbox_use_case=list_inbox_uc,
        get_mail_detail_use_case=get_detail_uc,
        get_unread_summary_use_case=get_unread_uc,
    )


def get_default_contacts_gateway(
    database_url: str | None = None,
) -> ContactsRepositoryPort:
    """Creates a SQLContactsGateway instance."""
    return SQLContactsGateway(database_url=database_url)


def get_contacts_controller(
    repository: ContactsRepositoryPort | None = None,
) -> ContactsController:
    """Builds and returns a ContactsController instance."""
    repo = repository or get_default_contacts_gateway()
    return ContactsController(
        list_contacts_use_case=ListContactsUseCase(repository=repo),
        get_contact_detail_use_case=GetContactDetailUseCase(repository=repo),
        create_contact_use_case=CreateContactUseCase(repository=repo),
        update_contact_use_case=UpdateContactUseCase(repository=repo),
        delete_contact_use_case=DeleteContactUseCase(repository=repo),
    )


def get_default_calendar_gateway(
    database_url: str | None = None,
) -> CalendarRepositoryPort:
    """Creates a SQLCalendarGateway instance."""
    return SQLCalendarGateway(database_url=database_url)


def get_calendar_controller(
    repository: CalendarRepositoryPort | None = None,
) -> CalendarController:
    """Builds and returns a CalendarController instance."""
    repo = repository or get_default_calendar_gateway()
    return CalendarController(
        list_events_use_case=ListCalendarEventsUseCase(repository=repo),
        get_upcoming_events_use_case=GetUpcomingEventsUseCase(repository=repo),
        get_event_detail_use_case=GetEventDetailUseCase(repository=repo),
        create_event_use_case=CreateCalendarEventUseCase(repository=repo),
        update_event_use_case=UpdateCalendarEventUseCase(repository=repo),
        delete_event_use_case=DeleteCalendarEventUseCase(repository=repo),
        check_availability_use_case=CheckAvailabilityUseCase(repository=repo),
    )
