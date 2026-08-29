"""Tests unitarios del gateway TelegramMailNotifierGateway.

Valida serialización del mensaje, headers y manejo de errores de red.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.gateways.telegram_mail_notifier_gateway import (
    TelegramMailNotifierGateway,
)
from src.domain.mail.entities import AnalisisEmail, EmailDetail, EntidadesDetectadas
from src.domain.mail.value_objects import CategoriaEmail, NivelPrioridad


def _analisis() -> AnalisisEmail:
    return AnalisisEmail(
        uid="1",
        categoria=CategoriaEmail.OPORTUNIDAD_COMERCIAL,
        prioridad=NivelPrioridad.ALTA,
        score=95,
        resumen_ejecutivo="Analizan proveedores para bajada de datos.",
        accion_sugerida="Responder proponiendo visita técnica.",
        entidades=EntidadesDetectadas(
            empresa="JTEKT AUTOMOTIVE ARGENTINA (Toyota Group)",
            contacto_nombre="Sol Gurzalé",
            contacto_cargo="Buyer",
            tipo_proyecto="Telemetría de Inyectoras",
        ),
        requiere_alerta=True,
        cuenta="datamaq",
    )


def _email() -> EmailDetail:
    return EmailDetail(
        uid="1",
        remitente="sol.gurzale@jtekt.onmicrosoft.com",
        asunto="Proyecto automatización",
        cuerpo_texto="cuerpo",
        carpeta="INBOX",
    )


def _respuesta_json(status: int) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_sin_token_no_op_false() -> None:
    """Dado gateway sin bot_token ni chat_id → no-op, retorna False."""
    gw = TelegramMailNotifierGateway()
    assert gw.notificar_oportunidad_email(_analisis(), _email()) is False


def test_envio_exitoso_payload_correcto() -> None:
    """Dado token/chat configurado y POST exitoso → True y payload con badges."""
    gw = TelegramMailNotifierGateway(bot_token="TOKEN_TEST", chat_id="CHAT_TEST")
    mock_urlopen = MagicMock(return_value=_respuesta_json(200))
    with patch("urllib.request.urlopen", mock_urlopen):
        ok = gw.notificar_oportunidad_email(_analisis(), _email())

    assert ok is True
    assert mock_urlopen.call_count == 1
    req = mock_urlopen.call_args[0][0]
    assert "TOKEN_TEST" in req.full_url
    body = json.loads(req.data.decode("utf-8"))
    assert body["chat_id"] == "CHAT_TEST"
    assert body["parse_mode"] == "Markdown"
    texto = body["text"]
    assert "OPORTUNIDAD B2B" in texto
    assert "Toyota Group" in texto
    assert "Buyer" in texto
    assert "95/100" in texto
    assert "ALTA" in texto
    assert "Responder" in texto


def test_respuesta_no_2xx_retorna_false() -> None:
    """Dado POST con status HTTP de error → False."""
    gw = TelegramMailNotifierGateway(bot_token="TOKEN_TEST", chat_id="CHAT_TEST")
    with patch("urllib.request.urlopen", MagicMock(return_value=_respuesta_json(500))):
        assert gw.notificar_oportunidad_email(_analisis(), _email()) is False


def test_error_de_red_retorna_false() -> None:
    """Dado fallo de red en urlopen → False sin propagar excepción."""
    gw = TelegramMailNotifierGateway(bot_token="TOKEN_TEST", chat_id="CHAT_TEST")
    with patch("urllib.request.urlopen", side_effect=OSError("boom")):
        assert gw.notificar_oportunidad_email(_analisis(), _email()) is False


@pytest.mark.parametrize(
    "prioridad,esperado",
    [
        (NivelPrioridad.ALTA, "🟢"),
        (NivelPrioridad.MEDIA, "🟡"),
        (NivelPrioridad.BAJA, "⚪"),
    ],
)
def test_badge_segun_prioridad(prioridad: NivelPrioridad, esperado: str) -> None:
    """Dado cada prioridad → badge de color correcto en el texto."""
    analisis = _analisis()
    analisis = AnalisisEmail(
        uid=analisis.uid,
        categoria=analisis.categoria,
        prioridad=prioridad,
        score=analisis.score,
        resumen_ejecutivo=analisis.resumen_ejecutivo,
        accion_sugerida=analisis.accion_sugerida,
        entidades=analisis.entidades,
        requiere_alerta=analisis.requiere_alerta,
        cuenta=analisis.cuenta,
    )
    texto = TelegramMailNotifierGateway._construir_mensaje(analisis, _email())
    assert esperado in texto
