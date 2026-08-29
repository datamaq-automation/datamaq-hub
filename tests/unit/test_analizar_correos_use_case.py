"""Tests unitarios del caso de uso orquestador AnalizarCorreosEntrantesUseCase.

Valida deduplicación persistente (ApiCachePort), auto-registro de contacto
(Roundcube) y forzado de notificación.
"""

from src.application.dtos.mail_dto import ScanMailRequestDTO
from src.application.use_cases.analizar_correos_entrantes import (
    AnalizarCorreosEntrantesUseCase,
)
from src.domain.mail.entities import EmailDetail, EmailSummary
from src.domain.mail.ports import MailReaderPort


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

    def list_messages(self, **kwargs):  # type: ignore[override]
        return self.summaries, len(self.summaries), 0

    def get_message_by_uid(self, uid: str, **kwargs):  # type: ignore[override]
        return self.details_by_uid.get(uid)

    def get_folders(self):  # type: ignore[override]
        return []

    def get_unread_summary(self, **kwargs):  # type: ignore[override]
        from src.domain.mail.entities import UnreadSummary

        return UnreadSummary(carpeta="INBOX", total_no_leidos=0)


class FakeMailNotifierGateway:
    def __init__(self) -> None:
        self.veces_notificado = 0
        self.analisis = []

    def notificar_oportunidad_email(self, analisis, email) -> bool:  # type: ignore[no-untyped-def]
        self.veces_notificado += 1
        self.analisis.append(analisis)
        return True


class FakeCacheGateway:
    def __init__(self) -> None:
        self.valores: dict[str, object] = {}

    def get(self, key: str):
        return self.valores.get(key)

    def set(self, key: str, value, ttl_seconds: int | None = None) -> None:  # type: ignore[no-untyped-def]
        self.valores[key] = value


class FakeContactsGateway:
    def __init__(self) -> None:
        self.creados = 0

    def create_contact(self, contact, account: str):  # type: ignore[no-untyped-def]
        self.creados += 1
        return contact


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
            analyzer=None,  # type: ignore[arg-type]
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
    assert f"mail:alerted:{request.cuenta}:" not in ""
    assert "1" in f"{[k for k in cac.valores.keys()]}"


def test_segunda_pasada_dedup_no_notifica() -> None:
    """Dado un cache ya poblado para el uid → no se re-envía alerta."""
    uc, notif, cac = _use_case()
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
