"""Gateway de notificación de oportunidades B2B a Telegram.

Implementa MailNotifierPort usando la Bot API de Telegram con urllib.request
(sin dependencias externas extra), siguiendo el patrón del gateway de leads.
"""

import json
import logging
import urllib.error
import urllib.request

from src.domain.mail.entities import AnalisisEmail, EmailDetail
from src.domain.mail.ports import MailNotifierPort
from src.domain.mail.value_objects import NivelPrioridad

logger = logging.getLogger(__name__)

_BADGES: dict[NivelPrioridad, str] = {
    NivelPrioridad.ALTA: "🟢",
    NivelPrioridad.MEDIA: "🟡",
    NivelPrioridad.BAJA: "⚪",
}


class TelegramMailNotifierGateway(MailNotifierPort):
    """Despacha alertas enriquecidas de oportunidad B2B a Telegram."""

    def __init__(
        self, bot_token: str | None = None, chat_id: str | None = None
    ) -> None:
        self._bot_token = (bot_token or "").strip()
        self._chat_id = (chat_id or "").strip()

    def notificar_oportunidad_email(
        self, analisis: AnalisisEmail, email: EmailDetail
    ) -> bool:
        if not self._bot_token or not self._chat_id:
            logger.info(
                "Telegram bot token o chat_id no configurado. Alerta de oportunidad omitida."
            )
            return False

        texto = self._construir_mensaje(analisis, email)

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": self._chat_id,
                "text": texto,
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
            logger.warning("Error al enviar alerta de oportunidad a Telegram: %s", exc)
            return False

    @staticmethod
    def _construir_mensaje(analisis: AnalisisEmail, email: EmailDetail) -> str:
        badge = _BADGES.get(analisis.prioridad, "⚪")
        ent = analisis.entidades
        empresa = ent.empresa or "No especificada"
        contacto = ent.contacto_nombre or "No especificado"
        cargo = ent.contacto_cargo or ""
        contacto_linea = f"{contacto} ({cargo})" if cargo else contacto
        tipo = ent.tipo_proyecto or "No especificado"

        return (
            "🚨 *NUEVA OPORTUNIDAD B2B ENTRANTE — DataMaq*\n\n"
            f"🏢 *Empresa:* {empresa}\n"
            f"👤 *Contacto:* {contacto_linea}\n"
            f"✉️ *Email:* {email.remitente}\n"
            f"🎯 *Asunto:* {email.asunto}\n"
            f"📊 *Prioridad:* {badge} {analisis.prioridad.value} (Score: {analisis.score}/100)\n"
            f"🏷️ *Tipo:* {tipo}\n\n"
            f"💡 *Resumen:*\n{analisis.resumen_ejecutivo}\n\n"
            f"⚡ *Acción Recomendada:*\n{analisis.accion_sugerida}\n\n"
            f"📅 *Fecha:* {email.fecha}"
        )
