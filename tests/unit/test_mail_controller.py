"""Unit tests for MailController."""

from src.adapters.controllers.mail_controller import MailController
from src.application.use_cases.get_mail_detail import GetMailDetailUseCase
from src.application.use_cases.get_unread_summary import GetUnreadSummaryUseCase
from src.application.use_cases.list_inbox_messages import ListInboxMessagesUseCase
from src.application.use_cases.list_mail_folders import ListMailFoldersUseCase
from tests.unit.test_mail_use_cases import FakeMailReaderGateway


def test_mail_controller_methods():
    gateway = FakeMailReaderGateway()
    controller = MailController(
        list_folders_use_case=ListMailFoldersUseCase(mail_reader=gateway),
        list_inbox_use_case=ListInboxMessagesUseCase(mail_reader=gateway),
        get_mail_detail_use_case=GetMailDetailUseCase(mail_reader=gateway),
        get_unread_summary_use_case=GetUnreadSummaryUseCase(mail_reader=gateway),
    )

    folders = controller.get_folders()
    assert len(folders) == 2

    inbox = controller.get_inbox_messages(
        folder="INBOX", limit=10, offset=0, sin_leer=False
    )
    assert inbox.carpeta == "INBOX"
    assert len(inbox.correos) == 2

    unread = controller.get_unread_summary(folder="INBOX", limit=5)
    assert unread.total_no_leidos == 1

    detail = controller.get_message_detail(uid="1", folder="INBOX")
    assert detail.uid == "1"
    assert detail.asunto == "Primer Correo"
