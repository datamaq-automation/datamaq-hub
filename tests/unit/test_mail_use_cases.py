"""Unit tests for mail use cases."""

import pytest

from src.application.use_cases.get_mail_detail import GetMailDetailUseCase
from src.application.use_cases.get_unread_summary import GetUnreadSummaryUseCase
from src.application.use_cases.list_inbox_messages import ListInboxMessagesUseCase
from src.application.use_cases.list_mail_folders import ListMailFoldersUseCase
from src.domain.mail.entities import (
    EmailAttachmentMetadata,
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)
from src.domain.mail.exceptions import EmailNotFoundError
from src.domain.mail.ports import MailReaderPort


class FakeMailReaderGateway(MailReaderPort):
    """In-memory mock gateway implementing MailReaderPort for unit testing."""

    def __init__(self) -> None:
        self.folders = [
            EmailFolder(nombre="INBOX", total_mensajes=2, no_leidos=1),
            EmailFolder(nombre="Sent", total_mensajes=5, no_leidos=0),
        ]
        self.messages = [
            EmailSummary(
                uid="1",
                remitente="remitente1@example.com",
                destinatarios=["user@datamaq.com.ar"],
                asunto="Primer Correo",
                fecha="2026-08-27T08:00:00",
                leido=True,
                tiene_adjuntos=False,
                carpeta="INBOX",
            ),
            EmailSummary(
                uid="2",
                remitente="remitente2@example.com",
                destinatarios=["user@datamaq.com.ar"],
                asunto="Segundo Correo No Leído",
                fecha="2026-08-27T09:00:00",
                leido=False,
                tiene_adjuntos=True,
                carpeta="INBOX",
            ),
        ]
        self.details: dict[str, EmailDetail] = {
            "1": EmailDetail(
                uid="1",
                remitente="remitente1@example.com",
                destinatarios=["user@datamaq.com.ar"],
                cc=[],
                asunto="Primer Correo",
                fecha="2026-08-27T08:00:00",
                leido=True,
                cuerpo_texto="Texto del primer correo",
                cuerpo_html="<p>Texto del primer correo</p>",
                adjuntos=[],
                carpeta="INBOX",
            ),
            "2": EmailDetail(
                uid="2",
                remitente="remitente2@example.com",
                destinatarios=["user@datamaq.com.ar"],
                cc=["copia@datamaq.com.ar"],
                asunto="Segundo Correo No Leído",
                fecha="2026-08-27T09:00:00",
                leido=False,
                cuerpo_texto="Texto del segundo correo con adjunto",
                cuerpo_html="<p>Texto del segundo correo con adjunto</p>",
                adjuntos=[
                    EmailAttachmentMetadata(
                        nombre="reporte.pdf",
                        content_type="application/pdf",
                        tamano_bytes=2048,
                    )
                ],
                carpeta="INBOX",
            ),
        }

    def get_folders(self) -> list[EmailFolder]:
        return self.folders

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[EmailSummary], int, int]:
        filtered = self.messages
        if unread_only:
            filtered = [m for m in filtered if not m.leido]
        if q:
            filtered = [m for m in filtered if q.lower() in m.asunto.lower()]
        sliced = filtered[offset : offset + limit]
        total_in_folder = len(self.messages)
        total_unread = len([m for m in self.messages if not m.leido])
        return sliced, total_in_folder, total_unread

    def get_message_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        detail = self.details.get(uid)
        if detail and not include_html:
            return EmailDetail(
                uid=detail.uid,
                remitente=detail.remitente,
                destinatarios=detail.destinatarios,
                cc=detail.cc,
                asunto=detail.asunto,
                fecha=detail.fecha,
                leido=detail.leido,
                cuerpo_texto=detail.cuerpo_texto,
                cuerpo_html="",
                adjuntos=detail.adjuntos,
                carpeta=detail.carpeta,
            )
        return detail

    def get_unread_summary(
        self, folder: str = "INBOX", limit: int = 5, q: str | None = None
    ) -> UnreadSummary:
        unreads = [m for m in self.messages if not m.leido]
        if q:
            unreads = [m for m in unreads if q.lower() in m.asunto.lower()]
        sliced = unreads[:limit]
        return UnreadSummary(
            carpeta=folder,
            total_no_leidos=len(unreads),
            ultimos_no_leidos=sliced,
        )


def test_list_mail_folders_use_case():
    gateway = FakeMailReaderGateway()
    use_case = ListMailFoldersUseCase(mail_reader=gateway)
    folders = use_case.execute()

    assert len(folders) == 2
    assert folders[0].nombre == "INBOX"
    assert folders[0].total_mensajes == 2
    assert folders[0].no_leidos == 1
    assert folders[1].nombre == "Sent"


def test_list_inbox_messages_use_case():
    gateway = FakeMailReaderGateway()
    use_case = ListInboxMessagesUseCase(mail_reader=gateway)

    # All messages
    resp = use_case.execute(folder="INBOX", limit=10, offset=0, unread_only=False)
    assert resp.carpeta == "INBOX"
    assert resp.total == 2
    assert resp.no_leidos == 1
    assert len(resp.correos) == 2

    # Unread only
    resp_unread = use_case.execute(folder="INBOX", limit=10, offset=0, unread_only=True)
    assert len(resp_unread.correos) == 1
    assert resp_unread.correos[0].uid == "2"
    assert resp_unread.correos[0].leido is False


def test_get_mail_detail_use_case_success():
    gateway = FakeMailReaderGateway()
    use_case = GetMailDetailUseCase(mail_reader=gateway)

    detail = use_case.execute(uid="2", folder="INBOX")
    assert detail.uid == "2"
    assert detail.asunto == "Segundo Correo No Leído"
    assert len(detail.adjuntos) == 1
    assert detail.adjuntos[0].nombre == "reporte.pdf"
    assert detail.adjuntos[0].tamano_bytes == 2048


def test_get_mail_detail_use_case_not_found():
    gateway = FakeMailReaderGateway()
    use_case = GetMailDetailUseCase(mail_reader=gateway)

    with pytest.raises(EmailNotFoundError) as exc_info:
        use_case.execute(uid="999", folder="INBOX")
    assert "999" in exc_info.value.message


def test_get_unread_summary_use_case():
    gateway = FakeMailReaderGateway()
    use_case = GetUnreadSummaryUseCase(mail_reader=gateway)

    summary = use_case.execute(folder="INBOX", limit=5)
    assert summary.carpeta == "INBOX"
    assert summary.total_no_leidos == 1
    assert len(summary.ultimos_no_leidos) == 1
    assert summary.ultimos_no_leidos[0].uid == "2"


def test_settings_mail_account_resolution():
    """Verifica que get_mail_account_config resuelva cuentas específicas y default."""
    from src.infrastructure.pydantic.config import MailAccountConfig, Settings

    settings = Settings(
        default_mail_account="datamaq",
        mail_imap_user="info@datamaq.com.ar",
        mail_imap_pass="corp_pass",
        mail_accounts={
            "abc": MailAccountConfig(
                host="imap.gmail.com",
                port=993,
                user="docente@abc.gob.ar",
                password="abc_app_password",
            )
        },
    )

    # 1. Resolver cuenta específica 'abc'
    abc_cfg = settings.get_mail_account_config("abc")
    assert abc_cfg.host == "imap.gmail.com"
    assert abc_cfg.user == "docente@abc.gob.ar"

    # 2. Resolver cuenta por defecto 'datamaq'
    default_cfg = settings.get_mail_account_config()
    assert default_cfg.user == "info@datamaq.com.ar"

    # 3. Cuenta inexistente lanza AccountNotFoundError
    from src.domain.mail.exceptions import AccountNotFoundError

    with pytest.raises(AccountNotFoundError) as exc_info:
        settings.get_mail_account_config("cuenta_desconocida")
    assert "cuenta_desconocida" in str(exc_info.value)
