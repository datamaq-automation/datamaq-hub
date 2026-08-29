"""Gateway de caché de lecturas IMAP (wrap de MailReaderPort).

Envuelve un ``MailReaderPort`` base (ej. ImapMailGateway) y antepone una capa de
caché (``ApiCachePort``) para aliviar el cuello de botella dominante del VPS: los
accesos IMAP ralentizan cada consulta (≈ 2.6 s). Solo cachea resúmenes contados y
listados de carpetas; el contenido volátil (inbox paginado, detalle por UID) se
delega directo al reader para no servir respuestas obsoletas.

Es un adapter puro: no importa ``src.infrastructure``. Las entidades de dominio
``frozen=True`` se serializan con ``dataclasses.asdict`` y se reconstruyen con
``dataclasses.replace`` en el hit.
"""

from dataclasses import asdict
from typing import Any, cast

from src.domain.cache.ports import ApiCachePort
from src.domain.mail.entities import (
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)
from src.domain.mail.ports import MailReaderPort


class CachedMailReaderGateway(MailReaderPort):
    """Implementa ``MailReaderPort`` con capa de caché para lecturas IMAP.

    Determinado el ``account`` en la construcción (alias resuelto por Settings),
    que forma parte de la clave canónica junto al folder.
    """

    def __init__(
        self,
        reader: MailReaderPort,
        cache: ApiCachePort,
        account: str,
    ) -> None:
        self._reader = reader
        self._cache = cache
        self._account = account

    def get_folders(self) -> list[EmailFolder]:
        key = f"mail:folders:{self._account}"
        cached = self._cache.get(key)
        if cached is not None:
            return [_reconstruir_email_folder(item) for item in cached]
        carpetas = self._reader.get_folders()
        self._cache.set(key, [asdict(item) for item in carpetas])
        return carpetas

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[EmailSummary], int, int]:
        return self._reader.list_messages(
            folder=folder,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
            q=q,
        )

    def get_message_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        return self._reader.get_message_by_uid(
            uid=uid,
            folder=folder,
            include_html=include_html,
            max_chars=max_chars,
        )

    def get_unread_summary(
        self,
        folder: str = "INBOX",
        limit: int = 5,
        q: str | None = None,
    ) -> UnreadSummary:
        key = f"mail:unread_summary:{self._account}:{folder}"
        cached = self._cache.get(key)
        if cached is not None:
            return _reconstruir_unread_summary(cached)
        resumen = self._reader.get_unread_summary(folder=folder, limit=limit, q=q)
        self._cache.set(key, asdict(resumen))
        return resumen


def _as_mapping(data: object) -> dict[str, Any]:
    """Devuelve ``data`` como dict JSON si lo es; en caso contrario, error."""
    if not isinstance(data, dict):
        raise TypeError("cached mail: se esperaba dict JSON")
    return cast("dict[str, Any]", data)


def _reconstruir_email_folder(data: object) -> EmailFolder:
    """Reconstruye ``EmailFolder`` desde un dict JSON."""
    crudo = _as_mapping(data)
    return EmailFolder(
        nombre=str(crudo.get("nombre", "")),
        total_mensajes=int(crudo.get("total_mensajes", 0)),
        no_leidos=int(crudo.get("no_leidos", 0)),
    )


def _reconstruir_email_summary(data: object) -> EmailSummary:
    """Reconstruye ``EmailSummary`` desde un dict JSON."""
    crudo = _as_mapping(data)
    return EmailSummary(
        uid=str(crudo.get("uid", "")),
        remitente=str(crudo.get("remitente", "")),
        destinatarios=list(crudo.get("destinatarios", [])),
        asunto=str(crudo.get("asunto", "")),
        fecha=str(crudo.get("fecha", "")),
        leido=bool(crudo.get("leido", False)),
        tiene_adjuntos=bool(crudo.get("tiene_adjuntos", False)),
        carpeta=str(crudo.get("carpeta", "INBOX")),
        snippet=str(crudo.get("snippet", "")),
    )


def _reconstruir_unread_summary(data: object) -> UnreadSummary:
    """Reconstruye ``UnreadSummary`` (y sus ``EmailSummary``) desde un dict JSON."""
    crudo = _as_mapping(data)
    ultimos = [
        _reconstruir_email_summary(item)
        for item in cast("list[object]", crudo.get("ultimos_no_leidos", []))
    ]
    return UnreadSummary(
        carpeta=str(crudo.get("carpeta", "")),
        total_no_leidos=int(crudo.get("total_no_leidos", 0)),
        ultimos_no_leidos=ultimos,
    )
