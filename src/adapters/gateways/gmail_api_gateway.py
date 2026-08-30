"""Gmail REST API Gateway implementing MailReaderPort using standard library urllib and base64."""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, cast

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
)
from src.domain.mail.ports import MailReaderPort


class GmailApiGateway(MailReaderPort):
    """Gateway that queries the Gmail REST API for Google Workspace and Gmail accounts."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        user_email: str = "me",
        timeout_seconds: int = 15,
        logger: LoggerPort | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.user_email = user_email
        self.timeout_seconds = timeout_seconds
        self._logger = logger or NullLogger()
        self._cached_token: str | None = None

    def _get_access_token(self) -> str:
        """Exchanges OAuth2 refresh token for a short-lived access token."""
        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise MailAuthenticationError(
                self.user_email,
                "Credenciales OAuth2 incompletas (requiere client_id, client_secret y refresh_token).",
            )

        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
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
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))
                token = body.get("access_token")
                if not token:
                    raise MailAuthenticationError(
                        self.user_email, "Respuesta OAuth2 sin access_token."
                    )
                self._cached_token = str(token)
                return self._cached_token
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise MailAuthenticationError(
                self.user_email,
                f"Error canjeando refresh_token en Google OAuth2 ({e.code}): {error_body}",
            ) from e
        except Exception as e:
            raise MailConnectionError(
                "oauth2.googleapis.com", 443, f"Error conectando a OAuth2: {e}"
            ) from e

    def _make_api_request(
        self, endpoint: str, query_params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Executes an authenticated GET request against the Gmail REST API."""
        access_token = self._get_access_token()
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/{endpoint}"
        if query_params:
            url += f"?{urllib.parse.urlencode(query_params)}"

        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise MailboxNotFoundError(endpoint) from e
            if e.code in (401, 403):
                err = e.read().decode("utf-8", errors="ignore")
                raise MailAuthenticationError(
                    self.user_email, f"Gmail API error ({e.code}): {err}"
                ) from e
            err = e.read().decode("utf-8", errors="ignore")
            raise MailConnectionError(
                "gmail.googleapis.com", 443, f"HTTP {e.code}: {err}"
            ) from e
        except Exception as e:
            raise MailConnectionError("gmail.googleapis.com", 443, str(e)) from e

    def get_folders(self) -> list[EmailFolder]:
        """Fetch all accessible Gmail labels with message counts."""
        data = self._make_api_request("labels")
        labels = cast(list[dict[str, Any]], data.get("labels", []))
        folders: list[EmailFolder] = []

        for label in labels:
            label_id = str(label.get("id", ""))
            if label_id in ("CHAT", "DRAFT"):
                continue
            name = str(label.get("name", label_id))
            try:
                detail = self._make_api_request(f"labels/{label_id}")
                total = int(detail.get("messagesTotal", 0))
                unread = int(detail.get("messagesUnread", 0))
                folders.append(
                    EmailFolder(
                        nombre=name,
                        total_mensajes=total,
                        no_leidos=unread,
                    )
                )
            except Exception as e:  # noqa: BLE001
                self._logger.debug("Error obteniendo label %s: %s", label_id, e)
                folders.append(EmailFolder(nombre=name, total_mensajes=0, no_leidos=0))

        folders.sort(key=lambda f: (0 if f.nombre.upper() == "INBOX" else 1, f.nombre))
        return folders

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[EmailSummary], int, int]:
        """List email summaries from a label/folder with optional search query."""
        query_parts: list[str] = []
        if folder.upper() == "INBOX":
            query_parts.append("in:inbox")
        else:
            query_parts.append(f'label:"{folder}"')

        if unread_only:
            query_parts.append("is:unread")

        if q and q.strip():
            query_parts.append(f"({q.strip()})")

        q_str = " ".join(query_parts)
        params = {"q": q_str, "maxResults": str(limit)}

        data = self._make_api_request("messages", params)
        raw_messages = cast(list[dict[str, Any]], data.get("messages", []))
        result_estimate = int(data.get("resultSizeEstimate", len(raw_messages)))

        unread_parts = list(query_parts)
        if not unread_only:
            unread_parts.append("is:unread")
        unread_data = self._make_api_request(
            "messages",
            {
                "q": " ".join(unread_parts),
                "maxResults": "1",
            },
        )
        total_unread = int(unread_data.get("resultSizeEstimate", 0))

        summaries: list[EmailSummary] = []
        for msg in raw_messages:
            msg_id = str(msg.get("id", ""))
            if not msg_id:
                continue
            try:
                meta = self._make_api_request(
                    f"messages/{msg_id}",
                    {"format": "metadata"},
                )
                snippet_val = str(meta.get("snippet", ""))[:150]
                payload = cast(dict[str, Any], meta.get("payload", {}))
                headers_list = cast(list[dict[str, str]], payload.get("headers", []))
                headers_dict: dict[str, str] = {
                    str(h["name"]).lower(): str(h["value"])
                    for h in headers_list
                    if "name" in h and "value" in h
                }
                label_ids = cast(list[str], meta.get("labelIds", []))

                from_val = headers_dict.get("from", "Desconocido")
                subject_val = headers_dict.get("subject", "")
                date_val = headers_dict.get("date", "")
                to_val = [headers_dict.get("to", "")] if "to" in headers_dict else []
                is_read = "UNREAD" not in label_ids

                has_attach = False
                parts_list = cast(list[dict[str, Any]], payload.get("parts", []))
                for part in parts_list:
                    if part.get("filename"):
                        has_attach = True
                        break

                summaries.append(
                    EmailSummary(
                        uid=msg_id,
                        remitente=from_val,
                        destinatarios=to_val,
                        asunto=subject_val,
                        fecha=date_val,
                        leido=is_read,
                        tiene_adjuntos=has_attach,
                        carpeta=folder,
                        snippet=snippet_val,
                    )
                )
            except Exception as e:  # noqa: BLE001
                self._logger.debug("Error obteniendo metadata de mensaje %s: %s", msg_id, e)

        return summaries, result_estimate, total_unread

    def get_message_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        """Fetch full email detail by ID with token optimization options."""
        try:
            data = self._make_api_request(f"messages/{uid}", {"format": "full"})
        except MailboxNotFoundError:
            return None

        payload = cast(dict[str, Any], data.get("payload", {}))
        headers_list = cast(list[dict[str, str]], payload.get("headers", []))
        headers: dict[str, str] = {
            str(h["name"]).lower(): str(h["value"])
            for h in headers_list
            if "name" in h and "value" in h
        }
        label_ids = cast(list[str], data.get("labelIds", []))

        from_val = headers.get("from", "Desconocido")
        to_val = [headers.get("to", "")] if "to" in headers else []
        cc_val = [headers.get("cc", "")] if "cc" in headers else []
        subject_val = headers.get("subject", "")
        date_val = headers.get("date", "")
        is_read = "UNREAD" not in label_ids

        body_text = ""
        body_html = ""
        attachments: list[EmailAttachmentMetadata] = []

        def extract_parts(part: dict[str, Any]):
            nonlocal body_text, body_html
            mime_type = str(part.get("mimeType", ""))
            filename = str(part.get("filename", ""))
            body = cast(dict[str, Any], part.get("body", {}))
            data_b64 = cast(str | None, body.get("data"))
            size = int(body.get("size", 0))

            if filename:
                attachments.append(
                    EmailAttachmentMetadata(
                        nombre=filename,
                        content_type=mime_type or "application/octet-stream",
                        tamano_bytes=size,
                    )
                )

            if data_b64:
                try:
                    decoded = base64.urlsafe_b64decode(data_b64 + "==").decode(
                        "utf-8", errors="ignore"
                    )
                    if mime_type == "text/plain" and not body_text:
                        body_text = decoded
                    elif mime_type == "text/html" and include_html and not body_html:
                        body_html = decoded
                except (ValueError, TypeError, UnicodeDecodeError):
                    pass

            for subpart in cast(list[dict[str, Any]], part.get("parts", [])):
                extract_parts(subpart)

        extract_parts(payload)

        if not body_text and not body_html:
            top_body = cast(dict[str, Any], payload.get("body", {}))
            top_data = cast(str | None, top_body.get("data"))
            if top_data:
                try:
                    body_text = base64.urlsafe_b64decode(top_data + "==").decode(
                        "utf-8", errors="ignore"
                    )
                except (ValueError, TypeError, UnicodeDecodeError):
                    pass

        if max_chars > 0 and len(body_text) > max_chars:
            body_text = (
                body_text[:max_chars]
                + f"\n\n[...Texto truncado por límite de {max_chars} caracteres...]"
            )

        return EmailDetail(
            uid=uid,
            remitente=from_val,
            destinatarios=to_val,
            cc=cc_val,
            asunto=subject_val,
            fecha=date_val,
            leido=is_read,
            cuerpo_texto=body_text,
            cuerpo_html=body_html if include_html else "",
            adjuntos=attachments,
            carpeta=folder,
        )

    def get_unread_summary(
        self, folder: str = "INBOX", limit: int = 5, q: str | None = None
    ) -> UnreadSummary:
        """Fetch count and brief list of recent unread messages."""
        messages, _total_folder, total_unread = self.list_messages(
            folder=folder, limit=limit, unread_only=True, q=q
        )
        return UnreadSummary(
            carpeta=folder,
            total_no_leidos=total_unread,
            ultimos_no_leidos=messages,
        )
