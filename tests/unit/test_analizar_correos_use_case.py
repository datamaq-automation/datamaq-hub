"""Tests unitarios del caso de uso orquestador AnalizarCorreosEntrantesUseCase.

Valida deduplicación persistente (ApiCachePort), auto-registro de contacto
(Roundcube) y forzado de notificación.
"""

from typing import Any

from src.application.dtos.mail_dto import ScanMailRequestDTO
from src.application.use_cases.analizar_correos_entrantes import (
    AnalizarCorreosEntrantesUseCase,
)
from src.domain.cache.ports import ApiCachePort
from src.domain.contacts.entities import Contact, ContactGroup
from src.domain.contacts.ports import ContactsRepositoryPort
from src.domain.mail.entities import (
    AnalisisEmail,
    EmailDetail,
    EmailSummary,
    UnreadSummary,
)
from src.domain.mail.ports import MailNotifierPort, MailReaderPort
from src.domain.mail.services import EmailOpportunityAnalyzerService


class FakeMailReaderGateway(MailReaderPort):
    """Reader en memoria que devuelve dos correos, uno de ellos oportunidad."""

    def __init__(self) -> None:
        self.summaries = [
            EmailSummary(
                uid="1",
                remitente="sol.gurzale@jtekt.onmicrosoft.com",
                asunto="Proyecto automatización",
                fecha="2026-08-26T17:45:00",
                leido=False,
                carpeta="INBOX",
            ),
            EmailSummary(
                uid="2",
                remitente="news@mailchimp.com",
                asunto="Newsletter",
                fecha="2026-08-26T09:00:00",
                leido=False,
                carpeta="INBOX",
            ),
        ]
        self.details_by_uid = {
            "1": EmailDetail(
                uid="1",
                remitente="sol.gurzale@jtekt.onmicrosoft.com",
                asunto="Proyecto automatización",
                fecha="2026-08-26T17:45:00",
                leido=False,
                cuerpo_texto=(
                    "Estimados, somos JTEKT Automotive Argentina (Toyota Group). "
                    "Buscamos bajada de datos de las lineas de inyeccion a PC local "
                    "y telemetria de tiempos de ciclo. Evaluando proveedores, "
                    "solicitamos cotizacion. Coordinamos reunion en planta.\n\n"
                    "Sol Gurzalé\nBuyer\n+54 11 5555-1234"
                ),
                carpeta="INBOX",
            ),
            "2": EmailDetail(
                uid="2",
                remitente="news@mailchimp.com",
                asunto="Newsletter",
                fecha="2026-08-26T09:00:00",
                leido=False,
                cuerpo_texto="Descubri nuevas tendencias.<a>Unsubscribe</a>",
                carpeta="INBOX",
            ),
        }

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[EmailSummary], int, int]:
        return self.summaries, len(self.summaries), len(self.summaries)

    def get_message_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        return self.details_by_uid.get(uid)

    def get_folders(self):
        from src.domain.mail.entities import EmailFolder

        return [EmailFolder(nombre="INBOX", total_mensajes=2, no_leidos=2)]

    def get_unread_summary(
        self,
        folder: str = "INBOX",
        limit: int = 5,
        q: str | None = None,
    ) -> UnreadSummary:
        return UnreadSummary(carpeta="INBOX", total_no_leidos=2)


class FakeMailNotifierGateway(MailNotifierPort):
    """Notifier falso que registra las alertas enviadas."""

    def __init__(self) -> None:
        self.veces_notificado = 0
        self.analisis: list = []

    def notificar_oportunidad_email(
        self, analisis: AnalisisEmail, email: EmailDetail
    ) -> bool:
        self.veces_notificado += 1
        self.analisis.append(analisis)
        return True


class FakeCacheGateway(ApiCachePort):
    """Cache en memoria con la interfaz de ApiCachePort."""

    def __init__(self) -> None:
        self.valores: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        return self.valores.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self.valores[key] = value


class FakeContactsGateway(ContactsRepositoryPort):
    """ContactsRepositoryPort falso que implementa todo el protocolo."""

    def __init__(self) -> None:
        self.creados = 0

    def list_contacts(
        self,
        account: str,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contact], int]:
        return [], 0

    def get_contact_by_id(self, contact_id: str, account: str) -> Contact | None:
        return None

    def create_contact(self, contact: Contact, account: str) -> Contact:
        self.creados += 1
        return contact

    def update_contact(self, contact: Contact, account: str) -> Contact:
        return contact

    def delete_contact(self, contact_id: str, account: str) -> bool:
        return False

    def list_groups(self, account: str) -> list[ContactGroup]:
        return []


def _use_case(
    notifier: FakeMailNotifierGateway | None = None,
    cache: FakeCacheGateway | None = None,
    contacts: FakeContactsGateway | None = None,
) -> tuple[AnalizarCorreosEntrantesUseCase, FakeMailNotifierGateway, FakeCacheGateway]:
    notif = notifier or FakeMailNotifierGateway()
    cac = cache or FakeCacheGateway()
    return (
        AnalizarCorreosEntrantesUseCase(
            mail_reader=FakeMailReaderGateway(),
            analyzer=EmailOpportunityAnalyzerService(),
            notifier=notif,
            cache=cac,
            contacts_repo=contacts,
        ),
        notif,
        cac,
    )


def test_primera_pasada_notifica_una_vez() -> None:
    """Dado un escaneo con 1 oportunidad → alerta enviada y cache poblado."""
    uc, notif, cac = _use_case()
    request = ScanMailRequestDTO()
    resultado = uc.execute(request)

    assert resultado.total_escaneados == 2
    assert resultado.total_oportunidades == 1
    assert resultado.alertas_enviadas == 1
    assert resultado.contactos_registrados == 0
    assert notif.veces_notificado == 1
    clave = f"mail:alerted:{request.cuenta}:1"
    assert clave in cac.valores


def test_segunda_pasada_dedup_no_notifica() -> None:
    """Dado un cache ya poblado para el uid → no se re-envía alerta."""
    uc, notif, _ = _use_case()
    request = ScanMailRequestDTO()
    uc.execute(request)
    notif.veces_notificado = 0

    segundo = uc.execute(request)

    assert segundo.alertas_enviadas == 0
    assert notif.veces_notificado == 0


def test_forzar_notificacion_omite_cache() -> None:
    """Dado forzar_notificacion=True → alerta enviada aún con cache vigente."""
    uc, notif, _ = _use_case()
    uc.execute(ScanMailRequestDTO())
    notif.veces_notificado = 0

    request = ScanMailRequestDTO(forzar_notificacion=True)
    resultado = uc.execute(request)

    assert resultado.alertas_enviadas == 1
    assert notif.veces_notificado == 1


def test_auto_registro_contacto() -> None:
    """Dado auto_registrar_contacto=True → se crea contacto en Roundcube."""
    contacts = FakeContactsGateway()
    uc, _, _ = _use_case(contacts=contacts)
    request = ScanMailRequestDTO(auto_registrar_contacto=True)
    resultado = uc.execute(request)

    assert resultado.contactos_registrados == 1
    assert contacts.creados == 1


def test_analizar_single_no_notifica() -> None:
    """Dado analizar_single → retorna DTO sin notificar ni cachear."""
    uc, notif, cac = _use_case()
    dto = uc.analizar_single(uid="1", cuenta="datamaq")

    assert dto.uid == "1"
    assert dto.requiere_alerta is True
    assert notif.veces_notificado == 0
    assert cac.valores == {}
