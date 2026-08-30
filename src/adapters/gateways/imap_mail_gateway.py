"""IMAP Mail Gateway implementing MailReaderPort using standard library imaplib and email."""

import imaplib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from typing import cast

from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.mail.entities import (
    EmailAttachmentMetadata,
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)
from src.domain.mail.exceptions import (
    MailAuthenticationError,
    MailboxNotFoundError,
    MailConnectionError,
    MailDomainException,
)
from src.domain.mail.ports import MailReaderPort
from src.domain.mail.services import MailDecoderService


class ImapMailGateway(MailReaderPort):
    """Gateway for querying IMAP servers in strict read-only mode (supports basic auth & OAuth2 XOAUTH2)."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 993,
        user: str = "",
        password: str = "",
        use_ssl: bool = True,
        timeout_seconds: int = 10,
        oauth2_client_id: str = "",
        oauth2_client_secret: str = "",
        oauth2_refresh_token: str = "",
        logger: LoggerPort | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self.timeout_seconds = timeout_seconds
        self.oauth2_client_id = oauth2_client_id
        self.oauth2_client_secret = oauth2_client_secret
        self.oauth2_refresh_token = oauth2_refresh_token
        self._logger = logger or NullLogger()

    def _safe_close(self, client: imaplib.IMAP4) -> None:
        """Closes IMAP mailbox without raising exceptions."""
        try:
            client.close()
        except (imaplib.IMAP4.error, OSError) as e:
            self._logger.debug("Error cerrando mailbox IMAP: %s", e)

    def _safe_logout(self, client: imaplib.IMAP4) -> None:
        """Logs out IMAP client session without raising exceptions."""
        try:
            client.logout()
        except (imaplib.IMAP4.error, OSError) as e:
            self._logger.debug("Error en logout IMAP: %s", e)

    def _get_oauth2_access_token(self) -> str:
        """Exchanges OAuth2 refresh token for a fresh short-lived access token."""
        if (
            not self.oauth2_client_id
            or not self.oauth2_client_secret
            or not self.oauth2_refresh_token
        ):
            raise MailAuthenticationError(
                self.user or "oauth2_user",
                "Credenciales OAuth2 incompletas (requiere oauth2_client_id, oauth2_client_secret y oauth2_refresh_token).",
            )

        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode(
            {
                "client_id": self.oauth2_client_id,
                "client_secret": self.oauth2_client_secret,
                "refresh_token": self.oauth2_refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
                access_token = body.get("access_token")
                if not access_token:
                    raise MailAuthenticationError(
                        self.user, "Respuesta OAuth2 sin access_token."
                    )
                return str(access_token)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise MailAuthenticationError(
                self.user,
                f"Error canjeando refresh_token en Google OAuth2 ({e.code}): {error_body}",
            ) from e
        except MailAuthenticationError:
            raise
        except Exception as e:
            raise MailAuthenticationError(
                self.user, f"Error conectando al endpoint de Google OAuth2: {e}"
            ) from e

    def _create_connection(self) -> imaplib.IMAP4:
        """Establishes an authenticated IMAP client session."""
        try:
            if self.use_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                client = imaplib.IMAP4_SSL(
                    host=self.host,
                    port=self.port,
                    ssl_context=ssl_context,
                    timeout=self.timeout_seconds,
                )
            else:
                client = imaplib.IMAP4(
                    host=self.host,
                    port=self.port,
                    timeout=self.timeout_seconds,
                )
        except TimeoutError as e:
            raise MailConnectionError(
                self.host,
                self.port,
                f"Timeout de conexión ({self.timeout_seconds}s): {e}",
            ) from e
        except (ConnectionRefusedError, OSError) as e:
            raise MailConnectionError(
                self.host, self.port, f"Conexión rechazada: {e}"
            ) from e

        # Autenticación XOAUTH2 si hay refresh_token
        if self.oauth2_refresh_token:
            access_token = self._get_oauth2_access_token()
            auth_bytes = (
                f"user={self.user}\x01auth=Bearer {access_token}\x01\x01".encode()
            )
            try:
                client.authenticate("XOAUTH2", lambda _: auth_bytes)
            except (imaplib.IMAP4.error, OSError, ValueError) as e:
                self._safe_logout(client)
                raise MailAuthenticationError(
                    self.user, f"Falla en autenticación XOAUTH2: {e}"
                ) from e
            return client

        # Autenticación básica estándar (usuario / contraseña)
        if not self.user or not self.password:
            self._safe_logout(client)
            raise MailAuthenticationError(
                self.user or "no_configurado",
                "Credenciales IMAP no configuradas (usuario o contraseña vacíos). Verifique la configuración de la cuenta en .env.",
            )

        try:
            client.login(self.user, self.password)
        except (imaplib.IMAP4.error, OSError, ValueError) as e:
            self._safe_logout(client)
            raise MailAuthenticationError(self.user, str(e)) from e

        return client

    def get_folders(self) -> list[EmailFolder]:
        """Fetch all accessible IMAP folders with counts of total and unread messages."""
        client = self._create_connection()
        folders: list[EmailFolder] = []
        try:
            typ, data = client.list()
            if typ != "OK" or not data:
                return [EmailFolder(nombre="INBOX", total_mensajes=0, no_leidos=0)]

            for item in data:
                if not item or not isinstance(item, bytes):
                    continue
                line = item.decode("utf-8", errors="ignore")
                parts = line.split(' "/" ')
                if len(parts) < 2:
                    parts = line.split(" ")
                    folder_name = parts[-1].strip('"')
                else:
                    folder_name = parts[1].strip().strip('"')

                if not folder_name:
                    continue

                total, unread = self._get_folder_status(client, folder_name)
                folders.append(
                    EmailFolder(
                        nombre=folder_name,
                        total_mensajes=total,
                        no_leidos=unread,
                    )
                )
        except MailDomainException:
            raise
        except (imaplib.IMAP4.error, OSError, ValueError) as e:
            self._logger.error("Error al listar carpetas IMAP: %s", e)
            raise MailDomainException(f"Error al listar carpetas IMAP: {e}") from e
        finally:
            self._safe_logout(client)

        return folders

    def _get_folder_status(
        self, client: imaplib.IMAP4, folder_name: str
    ) -> tuple[int, int]:
        """Retrieves total and unread message counts for a folder via STATUS command."""
        try:
            typ, status_data = client.status(f'"{folder_name}"', "(MESSAGES UNSEEN)")
            if typ == "OK" and status_data and status_data[0]:
                raw = status_data[0].decode("utf-8", errors="ignore")
                match_messages = re.search(r"MESSAGES\s+(\d+)", raw)
                match_unseen = re.search(r"UNSEEN\s+(\d+)", raw)
                total = int(match_messages.group(1)) if match_messages else 0
                unread = int(match_unseen.group(1)) if match_unseen else 0
                return total, unread
        except (imaplib.IMAP4.error, OSError, ValueError) as e:
            self._logger.debug(
                "Error obteniendo status de carpeta %s: %s", folder_name, e
            )
        return 0, 0

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[EmailSummary], int, int]:
        """List email summaries from a folder in strict read-only mode."""
        client = self._create_connection()
        messages: list[EmailSummary] = []
        try:
            typ, _ = client.select(f'"{folder}"', readonly=True)
            if typ != "OK":
                raise MailboxNotFoundError(folder)

            total_messages, total_unread = self._get_folder_status(client, folder)

            if q and q.strip():
                clean_q = q.strip().replace('"', '\\"')
                search_criteria = (
                    f'(UNSEEN TEXT "{clean_q}")'
                    if unread_only
                    else f'(TEXT "{clean_q}")'
                )
            else:
                search_criteria = "UNSEEN" if unread_only else "ALL"

            typ, search_data = client.uid("SEARCH", search_criteria)
            if typ != "OK" or not search_data or not search_data[0]:
                return [], total_messages, total_unread

            uids_raw = search_data[0].split()
            # Newest first (highest UID first)
            uids = [u.decode("utf-8") for u in reversed(uids_raw)]

            selected_uids = uids[offset : offset + limit]
            if not selected_uids:
                return [], total_messages, total_unread

            # Fetch headers without altering flags using BODY.PEEK
            for uid in selected_uids:
                typ, msg_data = client.uid(
                    "FETCH",
                    uid,
                    "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE CONTENT-TYPE)])",
                )
                if typ != "OK" or not msg_data:
                    continue

                summary = self._parse_summary_from_fetch(uid, folder, msg_data)
                if summary:
                    messages.append(summary)

        except MailDomainException:
            raise
        except (imaplib.IMAP4.error, OSError, ValueError) as e:
            self._logger.error(
                "Error al listar mensajes de la carpeta %s: %s", folder, e
            )
            raise MailDomainException(f"Error al consultar mensajes: {e}") from e
        finally:
            self._safe_close(client)
            self._safe_logout(client)

        return messages, total_messages, total_unread

    def get_message_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        """Fetch full email details by UID in read-only mode without mutating seen status."""
        client = self._create_connection()
        try:
            typ, _ = client.select(f'"{folder}"', readonly=True)
            if typ != "OK":
                raise MailboxNotFoundError(folder)

            # BODY.PEEK[] ensures seen status remains untouched
            typ, msg_data = client.uid("FETCH", uid, "(FLAGS BODY.PEEK[])")
            if typ != "OK" or not msg_data:
                return None

            return self._parse_detail_from_fetch(
                uid, folder, msg_data, include_html=include_html, max_chars=max_chars
            )

        except MailDomainException:
            raise
        except (imaplib.IMAP4.error, OSError, ValueError) as e:
            self._logger.error("Error al obtener mensaje %s de %s: %s", uid, folder, e)
            raise MailDomainException(
                f"Error al obtener detalle del correo: {e}"
            ) from e
        finally:
            self._safe_close(client)
            self._safe_logout(client)

    def get_unread_summary(
        self, folder: str = "INBOX", limit: int = 5, q: str | None = None
    ) -> UnreadSummary:
        """Fetch count and brief list of recent unread messages."""
        messages, _, total_unread = self.list_messages(
            folder=folder, limit=limit, offset=0, unread_only=True, q=q
        )
        return UnreadSummary(
            carpeta=folder,
            total_no_leidos=total_unread,
            ultimos_no_leidos=messages,
        )

    def _parse_summary_from_fetch(
        self, uid: str, folder: str, fetch_response: list[object]
    ) -> EmailSummary | None:
        """Parses an EmailSummary entity from raw IMAP fetch tuple."""
        raw_headers: bytes = b""
        flags_str: str = ""
        for part in fetch_response:
            if isinstance(part, tuple) and len(part) >= 2:
                t_part = cast(tuple[object, object], part)
                header_part = t_part[0]
                if isinstance(header_part, (bytes, bytearray)):
                    flags_str += bytes(header_part).decode("utf-8", errors="ignore")
                elif isinstance(header_part, str):
                    flags_str += header_part

                body_part = t_part[1]
                if isinstance(body_part, (bytes, bytearray)):
                    raw_headers += bytes(body_part)
            elif isinstance(part, (bytes, bytearray)):
                flags_str += bytes(part).decode("utf-8", errors="ignore")
            elif isinstance(part, str):
                flags_str += part

        if not raw_headers:
            return None

        msg = message_from_bytes(raw_headers)
        remitente = MailDecoderService.decode_header_str(msg.get("From", ""))
        asunto = MailDecoderService.decode_header_str(msg.get("Subject", ""))
        destinatarios = MailDecoderService.clean_email_list(msg.get("To", ""))

        fecha_iso = self._format_date_iso(msg.get("Date", ""))
        leido = "\\Seen" in flags_str

        ctype = msg.get_content_type()
        tiene_adjuntos = "multipart" in ctype

        return EmailSummary(
            uid=uid,
            remitente=remitente,
            destinatarios=destinatarios,
            asunto=asunto,
            fecha=fecha_iso,
            leido=leido,
            tiene_adjuntos=tiene_adjuntos,
            carpeta=folder,
            snippet="",
        )

    def _parse_detail_from_fetch(
        self,
        uid: str,
        folder: str,
        fetch_response: list[object],
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        """Parses full EmailDetail entity from complete RFC 822 MIME byte stream."""
        raw_email: bytes = b""
        flags_str: str = ""
        for part in fetch_response:
            if isinstance(part, tuple) and len(part) >= 2:
                t_part = cast(tuple[object, object], part)
                header_part = t_part[0]
                if isinstance(header_part, (bytes, bytearray)):
                    flags_str += bytes(header_part).decode("utf-8", errors="ignore")
                elif isinstance(header_part, str):
                    flags_str += header_part

                body_part = t_part[1]
                if isinstance(body_part, (bytes, bytearray)):
                    raw_email += bytes(body_part)
            elif isinstance(part, (bytes, bytearray)):
                flags_str += bytes(part).decode("utf-8", errors="ignore")
            elif isinstance(part, str):
                flags_str += part

        if not raw_email:
            return None

        msg = message_from_bytes(raw_email)
        remitente = MailDecoderService.decode_header_str(msg.get("From", ""))
        asunto = MailDecoderService.decode_header_str(msg.get("Subject", ""))
        destinatarios = MailDecoderService.clean_email_list(msg.get("To", ""))
        cc = MailDecoderService.clean_email_list(msg.get("Cc", ""))
        fecha_iso = self._format_date_iso(msg.get("Date", ""))
        leido = "\\Seen" in flags_str

        cuerpo_texto = ""
        cuerpo_html = ""
        adjuntos: list[EmailAttachmentMetadata] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                filename = part.get_filename()

                if filename:
                    decoded_filename = MailDecoderService.decode_header_str(filename)
                    payload = part.get_payload(decode=True)
                    size = len(payload) if isinstance(payload, bytes) else 0
                    adjuntos.append(
                        EmailAttachmentMetadata(
                            nombre=decoded_filename,
                            content_type=content_type,
                            tamano_bytes=size,
                        )
                    )
                elif "attachment" in content_disposition:
                    decoded_filename = MailDecoderService.decode_header_str(
                        filename or "adjunto_sin_nombre"
                    )
                    payload = part.get_payload(decode=True)
                    size = len(payload) if isinstance(payload, bytes) else 0
                    adjuntos.append(
                        EmailAttachmentMetadata(
                            nombre=decoded_filename,
                            content_type=content_type,
                            tamano_bytes=size,
                        )
                    )
                elif content_type == "text/plain" and not cuerpo_texto:
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        charset = part.get_content_charset() or "utf-8"
                        cuerpo_texto = self._decode_payload(payload, charset)
                elif content_type == "text/html" and include_html and not cuerpo_html:
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        charset = part.get_content_charset() or "utf-8"
                        cuerpo_html = self._decode_payload(payload, charset)
        else:
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                charset = msg.get_content_charset() or "utf-8"
                decoded_body = self._decode_payload(payload, charset)
                if msg.get_content_type() == "text/html":
                    if include_html:
                        cuerpo_html = decoded_body
                else:
                    cuerpo_texto = decoded_body

        sanitized_text = MailDecoderService.sanitize_text(cuerpo_texto)
        if max_chars > 0 and len(sanitized_text) > max_chars:
            sanitized_text = (
                sanitized_text[:max_chars]
                + f"\n\n[...Texto truncado por límite de {max_chars} caracteres...]"
            )

        return EmailDetail(
            uid=uid,
            remitente=remitente,
            destinatarios=destinatarios,
            cc=cc,
            asunto=asunto,
            fecha=fecha_iso,
            leido=leido,
            cuerpo_texto=sanitized_text,
            cuerpo_html=cuerpo_html.strip() if include_html else "",
            adjuntos=adjuntos,
            carpeta=folder,
        )

    def _decode_payload(self, payload: bytes, charset: str) -> str:
        """Safely decodes payload bytes to unicode with fallback encodings."""
        try:
            return payload.decode(charset, errors="replace")
        except (LookupError, ValueError, UnicodeDecodeError):
            try:
                return payload.decode("utf-8", errors="replace")
            except (LookupError, ValueError, UnicodeDecodeError):
                return payload.decode("latin-1", errors="replace")

    def _format_date_iso(self, date_header: str) -> str:
        """Converts RFC 2822 date header string to ISO 8601 string."""
        if not date_header:
            return ""
        try:
            dt = parsedate_to_datetime(date_header)
            return dt.isoformat()
        except (ValueError, TypeError, OverflowError, IndexError):
            return str(date_header).strip()
