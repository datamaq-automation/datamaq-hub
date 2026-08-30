"""Gateway implementation for dispatching lead notifications to Telegram."""

import json
import urllib.error
import urllib.request

from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.leads.entities import Lead
from src.domain.leads.ports import LeadNotifierPort


class TelegramLeadNotifierGateway(LeadNotifierPort):
    """Dispatches instant notifications to a Telegram chat or channel via Bot API."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        self._bot_token = (bot_token or "").strip()
        self._chat_id = (chat_id or "").strip()
        self._logger = logger or NullLogger()

    def notificar_nuevo_lead(self, lead: Lead) -> bool:
        if not self._bot_token or not self._chat_id:
            self._logger.info(
                "Telegram bot token o chat_id no configurado. Notificación omitida."
            )
            return True

        text_msg = (
            "🚀 *Nuevo Lead Comercial Recibido en DataMaq*\n\n"
            f"👤 *Nombre:* {lead.nombre}\n"
            f"🏢 *Empresa:* {lead.empresa or 'No especificada'}\n"
            f"📞 *Teléfono:* {lead.telefono or 'No especificado'}\n"
            f"✉️ *Email:* {lead.email or 'No especificado'}\n"
            f"🌐 *Fuente:* {lead.fuente.channel}"
            + (f" (Campaña: {lead.fuente.campaign})" if lead.fuente.campaign else "")
            + f"\n📝 *Consulta:* {lead.mensaje or 'Sin mensaje adicional'}\n"
        )

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": self._chat_id,
                "text": text_msg,
                "parse_mode": "Markdown",
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return 200 <= resp.status < 300
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
        ) as exc:
            self._logger.warning(
                "Error al enviar notificación de lead a Telegram: %s", exc
            )
            return False
