"""RED suite para CachedMailReaderGateway (wrapper de caché de lecturas IMAP)."""

from __future__ import annotations

from src.adapters.gateways.cached_mail_reader_gateway import (
    CachedMailReaderGateway,
)
from src.domain.cache.ports import ApiCachePort
from src.domain.mail.entities import (
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)
from src.domain.mail.ports import MailReaderPort


class FakeCache(ApiCachePort):
    """Apila valores en memoria simulando la serialización JSON del gateway real."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}
        self.set_calls: list[str] = []
        self.get_calls: list[str] = []

    def get(self, key: str) -> object | None:
        self.get_calls.append(key)
        return self._store.get(key)

    def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        self.set_calls.append(key)
        self._store[key] = value


class FakeReader(MailReaderPort):
    """Reader con contadores de invocación para verificar hits y passthrough."""

    def __init__(self) -> None:
        self.unread_calls = 0
        self.folders_calls = 0
        self.list_calls = 0
        self.detail_calls = 0
        self.fail_unread = False

    def get_folders(self) -> list[EmailFolder]:
        self.folders_calls += 1
        return [EmailFolder(nombre="INBOX", total_mensajes=10, no_leidos=3)]

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[EmailSummary], int, int]:
        self.list_calls += 1
        return ([], 0, 0)

    def get_message_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        self.detail_calls += 1
        return None

    def get_unread_summary(
        self,
        folder: str = "INBOX",
        limit: int = 5,
        q: str | None = None,
    ) -> UnreadSummary:
        self.unread_calls += 1
        if self.fail_unread:
            raise RuntimeError("IMAP caído")
        return UnreadSummary(
            carpeta=folder,
            total_no_leidos=201,
            ultimos_no_leidos=[EmailSummary(uid="1", remitente="a@b.c", asunto="Hola")],
        )


def _build() -> tuple[CachedMailReaderGateway, FakeReader, FakeCache]:
    reader = FakeReader()
    cache = FakeCache()
    gateway = CachedMailReaderGateway(reader=reader, cache=cache, account="abc")
    gateway.get_unread_summary(folder="INBOX")  # poblar caché en primer uso
    return gateway, reader, cache


def test_unread_summary_hit_sirve_desde_cache_sin_invocar_reader() -> None:
    gateway, reader, cache = _build()
    primer_invoca = reader.unread_calls
    resultado = gateway.get_unread_summary(folder="INBOX")
    assert resultado.total_no_leidos == 201
    assert reader.unread_calls == primer_invoca
    assert "mail:unread_summary:abc:INBOX" in cache.get_calls


def test_unread_summary_miss_delega_y_poblifica() -> None:
    reader = FakeReader()
    cache = FakeCache()
    gateway = CachedMailReaderGateway(reader=reader, cache=cache, account="abc")
    resultado = gateway.get_unread_summary(folder="SPAM")
    assert resultado.total_no_leidos == 201
    assert reader.unread_calls == 1
    assert "mail:unread_summary:abc:SPAM" in cache.set_calls


def test_unread_summary_con_error_no_poblifica_cache() -> None:
    reader = FakeReader()
    reader.fail_unread = True
    cache = FakeCache()
    gateway = CachedMailReaderGateway(reader=reader, cache=cache, account="abc")
    try:
        gateway.get_unread_summary(folder="INBOX")
    except RuntimeError:
        pass
    else:
        raise AssertionError("se esperaba RuntimeError del reader")
    assert not cache.set_calls


def test_folders_hit_sirve_desde_cache() -> None:
    reader = FakeReader()
    cache = FakeCache()
    gateway = CachedMailReaderGateway(reader=reader, cache=cache, account="abc")
    gateway.get_folders()
    invoca = reader.folders_calls
    carpetas = gateway.get_folders()
    assert carpetas[0].nombre == "INBOX"
    assert reader.folders_calls == invoca
    assert "mail:folders:abc" in cache.get_calls


def test_list_messages_y_detalle_son_passthrough() -> None:
    reader = FakeReader()
    cache = FakeCache()
    gateway = CachedMailReaderGateway(reader=reader, cache=cache, account="abc")
    gateway.list_messages(limit=5)
    gateway.get_message_by_uid(uid="123")
    assert reader.list_calls == 1
    assert reader.detail_calls == 1
    assert not cache.set_calls
