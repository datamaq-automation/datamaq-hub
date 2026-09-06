"""Gateway de notificación de oportunidades B2B a Telegram.

Implementa MailNotifierPort usando la Bot API de Telegram con urllib.request
(sin dependencias externas extra), siguiendo el patrón del gateway de leads.
"""

import json
import urllib.error
import urllib.request

from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.mail.entities import AnalisisEmail, EmailDetail
from src.domain.mail.ports import MailNotifierPort
from src.domain.mail.services import MailDecoderService, _partes_remitente
from src.domain.mail.value_objects import NivelPrioridad

# Caracteres del cuerpo real que se incluyen en la alerta. El resumen ejecutivo es
# una plantilla determinística: sin este bloque el mensaje nunca dice qué pide el correo.
_CUERPO_MAX_CHARS = 400

_BADGES: dict[NivelPrioridad, str] = {
    NivelPrioridad.ALTA: "🟢",
    NivelPrioridad.MEDIA: "🟡",
    NivelPrioridad.BAJA: "⚪",
}


class TelegramMailNotifierGateway(MailNotifierPort):
    """Despacha alertas enriquecidas de oportunidad B2B a Telegram."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        self._bot_token = (bot_token or "").strip()
        self._chat_id = (chat_id or "").strip()
        self._logger = logger or NullLogger()

    def notificar_oportunidad_email(
        self, analisis: AnalisisEmail, email: EmailDetail
    ) -> bool:
        if not self._bot_token or not self._chat_id:
            self._logger.info(
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
            self._logger.warning(
                "Error al enviar alerta de oportunidad a Telegram: %s", exc
            )
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

        # El nombre visible ya va en la línea de Contacto: acá interesa la dirección.
        _display, direccion = _partes_remitente(email.remitente)
        direccion = direccion or email.remitente

        cuerpo = MailDecoderService.build_snippet(
            raw_body=email.cuerpo_texto.encode("utf-8", errors="replace"),
            content_type="text/plain",
            max_chars=_CUERPO_MAX_CHARS,
        )
        bloque_cuerpo = f"📄 *Cuerpo:*\n{cuerpo}\n\n" if cuerpo else ""

        return (
            "🚨 *NUEVA OPORTUNIDAD B2B ENTRANTE — DataMaq*\n\n"
            f"🏢 *Empresa:* {empresa}\n"
            f"👤 *Contacto:* {contacto_linea}\n"
            f"✉️ *Email:* {direccion}\n"
            f"🎯 *Asunto:* {email.asunto}\n"
            f"📊 *Prioridad:* {badge} {analisis.prioridad.value} (Score: {analisis.score}/100)\n"
            f"🏷️ *Tipo:* {tipo}\n\n"
            f"{bloque_cuerpo}"
            f"💡 *Resumen:*\n{analisis.resumen_ejecutivo}\n\n"
            f"⚡ *Acción Recomendada:*\n{analisis.accion_sugerida}\n\n"
            f"📅 *Fecha:* {email.fecha}"
        )
