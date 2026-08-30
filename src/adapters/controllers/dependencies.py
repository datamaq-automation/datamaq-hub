"""Dependency injection providers for controllers and use cases."""

from functools import lru_cache

from src.adapters.controllers.health_controller import HealthController
from src.adapters.controllers.horarios_docencia_controller import (
    HorariosDocenciaController,
)
from src.adapters.controllers.mail_controller import MailController
from src.adapters.controllers.receipt_controller import ReceiptController
from src.adapters.controllers.simulation_controller import SimulationController
from src.adapters.controllers.tools_controller import ToolsController
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
from src.adapters.gateways.sql_recibo_gateway import SQLReciboGateway
from src.application.use_cases.actualizar_designacion import (
    ActualizarDesignacionUseCase,
)
from src.application.use_cases.cesar_designacion import CesarDesignacionUseCase
from src.application.use_cases.conciliar_recibo import ConciliarReciboUseCase
from src.application.use_cases.consultar_designaciones_vigentes import (
    ConsultarDesignacionesVigentesUseCase,
)
from src.application.use_cases.consultar_historial_docente import (
    ConsultarHistorialDocenteUseCase,
)
from src.application.use_cases.crear_designaciones_desde_recibo import (
    CrearDesignacionesDesdeReciboUseCase,
)
from src.application.use_cases.eliminar_designacion import EliminarDesignacionUseCase
from src.application.use_cases.eliminar_recibo import EliminarReciboUseCase
from src.application.use_cases.get_mail_detail import GetMailDetailUseCase
from src.application.use_cases.get_unread_summary import GetUnreadSummaryUseCase
from src.application.use_cases.list_inbox_messages import ListInboxMessagesUseCase
from src.application.use_cases.list_mail_folders import ListMailFoldersUseCase
from src.application.use_cases.listar_designaciones import (
    ListarDesignacionesUseCase,
)
from src.application.use_cases.listar_recibos import ListarRecibosUseCase
from src.application.use_cases.obtener_recibo import ObtenerReciboUseCase
from src.application.use_cases.parse_receipt import ParseReceiptUseCase
from src.application.use_cases.project_salary import ProjectSalaryUseCase
from src.application.use_cases.proyectar_sueldo_docente_vigente import (
    ProyectarSueldoDocenteVigenteUseCase,
)
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
from src.domain.recibos.ports import (
    PDFExtractorPort,
    ReceiptParserRegistryPort,
    ReciboRepositoryPort,
)


@lru_cache
def get_pdf_extractor_gateway() -> PDFExtractorPort:
    return PdfPlumberExtractorGateway()


@lru_cache
def get_receipt_parser_registry_gateway() -> ReceiptParserRegistryPort:
    return ReceiptParserRegistryGateway()


@lru_cache
def get_recibo_repository_gateway() -> ReciboRepositoryPort:
    return SQLReciboGateway()


def get_parse_receipt_use_case() -> ParseReceiptUseCase:
    extractor = get_pdf_extractor_gateway()
    parser_registry = get_receipt_parser_registry_gateway()
    repo = get_recibo_repository_gateway()
    return ParseReceiptUseCase(
        extractor=extractor, parser_registry=parser_registry, repository=repo
    )


def get_obtener_recibo_use_case() -> ObtenerReciboUseCase:
    return ObtenerReciboUseCase(repository=get_recibo_repository_gateway())


def get_listar_recibos_use_case() -> ListarRecibosUseCase:
    return ListarRecibosUseCase(repository=get_recibo_repository_gateway())


def get_eliminar_recibo_use_case() -> EliminarReciboUseCase:
    return EliminarReciboUseCase(repository=get_recibo_repository_gateway())


def get_conciliar_recibo_use_case() -> ConciliarReciboUseCase:
    return ConciliarReciboUseCase(
        recibo_repository=get_recibo_repository_gateway(),
        designacion_repository=get_designacion_docente_repository_gateway(),
    )


def get_crear_designaciones_desde_recibo_use_case() -> (
    CrearDesignacionesDesdeReciboUseCase
):
    return CrearDesignacionesDesdeReciboUseCase(
        recibo_repository=get_recibo_repository_gateway(),
        designacion_repository=get_designacion_docente_repository_gateway(),
    )


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
    return ReceiptController(
        parse_use_case=get_parse_receipt_use_case(),
        obtener_use_case=get_obtener_recibo_use_case(),
        listar_use_case=get_listar_recibos_use_case(),
        eliminar_use_case=get_eliminar_recibo_use_case(),
        conciliar_use_case=get_conciliar_recibo_use_case(),
        crear_desde_recibo_use_case=get_crear_designaciones_desde_recibo_use_case(),
    )


def get_proyectar_sueldo_docente_vigente_use_case() -> (
    ProyectarSueldoDocenteVigenteUseCase
):
    designacion_repo = get_designacion_docente_repository_gateway()
    recibo_repo = get_recibo_repository_gateway()
    paritaria_repo = get_paritaria_repository_gateway()
    motor = get_motor_liquidacion_service()
    return ProyectarSueldoDocenteVigenteUseCase(
        designacion_repository=designacion_repo,
        recibo_repository=recibo_repo,
        paritaria_repo=paritaria_repo,
        motor=motor,
    )


def get_simulation_controller() -> SimulationController:
    use_case = get_project_salary_use_case()
    cuit_use_case = get_proyectar_sueldo_docente_vigente_use_case()
    return SimulationController(
        project_use_case=use_case,
        project_by_cuit_use_case=cuit_use_case,
    )


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


def get_listar_designaciones_use_case() -> ListarDesignacionesUseCase:
    repo = get_designacion_docente_repository_gateway()
    return ListarDesignacionesUseCase(repository=repo)


def get_actualizar_designacion_use_case() -> ActualizarDesignacionUseCase:
    repo = get_designacion_docente_repository_gateway()
    return ActualizarDesignacionUseCase(repository=repo)


def get_eliminar_designacion_use_case() -> EliminarDesignacionUseCase:
    repo = get_designacion_docente_repository_gateway()
    return EliminarDesignacionUseCase(repository=repo)


def get_horarios_docencia_controller() -> HorariosDocenciaController:
    repo = get_designacion_docente_repository_gateway()
    validar_uc = get_validar_horarios_use_case()
    registrar_uc = get_registrar_designacion_use_case()
    cesar_uc = get_cesar_designacion_use_case()
    vigentes_uc = get_consultar_vigentes_use_case()
    historial_uc = get_consultar_historial_use_case()
    listar_uc = get_listar_designaciones_use_case()
    actualizar_uc = get_actualizar_designacion_use_case()
    eliminar_uc = get_eliminar_designacion_use_case()
    return HorariosDocenciaController(
        validar_use_case=validar_uc,
        registrar_use_case=registrar_uc,
        cesar_use_case=cesar_uc,
        consultar_vigentes_use_case=vigentes_uc,
        consultar_historial_use_case=historial_uc,
        listar_use_case=listar_uc,
        actualizar_use_case=actualizar_uc,
        eliminar_use_case=eliminar_uc,
        repository=repo,
    )


from src.adapters.controllers.calendar_controller import CalendarController
from src.adapters.controllers.contacts_controller import ContactsController
from src.adapters.controllers.leads_controller import LeadsController
from src.adapters.gateways.sql_calendar_gateway import SQLCalendarGateway
from src.adapters.gateways.sql_contacts_gateway import SQLContactsGateway
from src.adapters.gateways.telegram_lead_notifier_gateway import (
    TelegramLeadNotifierGateway,
)
from src.application.use_cases.check_availability import CheckAvailabilityUseCase
from src.application.use_cases.create_calendar_event import (
    CreateCalendarEventUseCase,
)
from src.application.use_cases.create_contact import CreateContactUseCase
from src.application.use_cases.delete_calendar_event import (
    DeleteCalendarEventUseCase,
)
from src.application.use_cases.delete_contact import DeleteContactUseCase
from src.application.use_cases.exportar_contactos_vcard import (
    ExportarContactosVCardUseCase,
)
from src.application.use_cases.get_contact_detail import GetContactDetailUseCase
from src.application.use_cases.get_event_detail import GetEventDetailUseCase
from src.application.use_cases.get_upcoming_events import (
    GetUpcomingEventsUseCase,
)
from src.application.use_cases.ingestar_lead import IngestarLeadUseCase
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
from src.domain.leads.ports import LeadNotifierPort


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
        export_vcard_use_case=ExportarContactosVCardUseCase(contacts_repo=repo),
    )


def get_default_lead_notifier_gateway(
    bot_token: str | None = None, chat_id: str | None = None
) -> LeadNotifierPort:
    """Creates a default TelegramLeadNotifierGateway instance."""
    return TelegramLeadNotifierGateway(bot_token=bot_token, chat_id=chat_id)


def get_leads_controller(
    contacts_repo: ContactsRepositoryPort | None = None,
    calendar_repo: CalendarRepositoryPort | None = None,
    notifier: LeadNotifierPort | None = None,
) -> LeadsController:
    """Builds and returns a LeadsController instance."""
    c_repo = contacts_repo or get_default_contacts_gateway()
    cal_repo = calendar_repo or get_default_calendar_gateway()
    notif = notifier or get_default_lead_notifier_gateway()
    use_case = IngestarLeadUseCase(
        contacts_repo=c_repo, calendar_repo=cal_repo, notifier=notif
    )
    return LeadsController(ingestar_lead_uc=use_case)


from src.application.use_cases.consultar_agenda_docente import (
    ConsultarAgendaDocenteUseCase,
)
from src.application.use_cases.sincronizar_agenda_docente import (
    SincronizarAgendaDocenteUseCase,
)


def get_default_calendar_gateway(
    database_url: str | None = None,
) -> CalendarRepositoryPort:
    """Creates a SQLCalendarGateway instance."""
    return SQLCalendarGateway(database_url=database_url)


def get_calendar_controller(
    repository: CalendarRepositoryPort | None = None,
    designacion_repository: DesignacionDocenteRepositoryPort | None = None,
) -> CalendarController:
    """Builds and returns a CalendarController instance."""
    repo = repository or get_default_calendar_gateway()
    doc_repo = designacion_repository or get_designacion_docente_repository_gateway()
    return CalendarController(
        list_events_use_case=ListCalendarEventsUseCase(repository=repo),
        get_upcoming_events_use_case=GetUpcomingEventsUseCase(repository=repo),
        get_event_detail_use_case=GetEventDetailUseCase(repository=repo),
        create_event_use_case=CreateCalendarEventUseCase(repository=repo),
        update_event_use_case=UpdateCalendarEventUseCase(repository=repo),
        delete_event_use_case=DeleteCalendarEventUseCase(repository=repo),
        check_availability_use_case=CheckAvailabilityUseCase(repository=repo),
        sincronizar_docencia_use_case=SincronizarAgendaDocenteUseCase(
            designacion_repo=doc_repo, calendar_repo=repo
        ),
        consultar_docencia_use_case=ConsultarAgendaDocenteUseCase(calendar_repo=repo),
    )


from src.adapters.controllers.agenda_controller import AgendaController
from src.adapters.controllers.tarea_controller import TareaController
from src.adapters.gateways.sql_tarea_gateway import SQLTareaGateway
from src.application.use_cases.actualizar_tarea import ActualizarTareaUseCase
from src.application.use_cases.completar_tarea import CompletarTareaUseCase
from src.application.use_cases.crear_tarea import CrearTareaUseCase
from src.application.use_cases.eliminar_tarea import EliminarTareaUseCase
from src.application.use_cases.generar_tareas_desde_recibo import (
    GenerarTareasDesdeReciboUseCase,
)
from src.application.use_cases.listar_tareas import ListarTareasUseCase
from src.application.use_cases.obtener_briefing_diario import (
    ObtenerBriefingDiarioUseCase,
)
from src.application.use_cases.obtener_tarea import ObtenerTareaUseCase
from src.domain.tareas.ports import TareaRepositoryPort


@lru_cache
def get_default_tarea_gateway(database_url: str | None = None) -> TareaRepositoryPort:
    return SQLTareaGateway(database_url=database_url)


def get_tarea_controller() -> TareaController:
    repo = get_default_tarea_gateway()
    r_repo = get_recibo_repository_gateway()
    d_repo = get_designacion_docente_repository_gateway()
    return TareaController(
        crear_use_case=CrearTareaUseCase(repository=repo),
        obtener_use_case=ObtenerTareaUseCase(repository=repo),
        listar_use_case=ListarTareasUseCase(repository=repo),
        actualizar_use_case=ActualizarTareaUseCase(repository=repo),
        completar_use_case=CompletarTareaUseCase(repository=repo),
        eliminar_use_case=EliminarTareaUseCase(repository=repo),
        generar_desde_recibo_use_case=GenerarTareasDesdeReciboUseCase(
            recibo_repository=r_repo,
            designacion_repository=d_repo,
            tarea_repository=repo,
        ),
    )


def get_agenda_controller() -> AgendaController:
    d_repo = get_designacion_docente_repository_gateway()
    t_repo = get_default_tarea_gateway()
    c_repo = get_default_calendar_gateway()
    use_case = ObtenerBriefingDiarioUseCase(
        designacion_repository=d_repo,
        tarea_repository=t_repo,
        calendar_repository=c_repo,
    )
    return AgendaController(obtener_briefing_use_case=use_case)


@lru_cache
def get_tools_controller() -> ToolsController:
    """Proveedor de dependencias para ToolsController."""
    from src.application.use_cases.calcular_recargo_cos_fi import (
        CalcularRecargoCosFiUseCase,
    )

    return ToolsController(calcular_cos_fi_use_case=CalcularRecargoCosFiUseCase())
