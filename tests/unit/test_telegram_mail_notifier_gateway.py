"""Tests unitarios del gateway TelegramMailNotifierGateway.

Valida serialización del mensaje, headers y manejo de errores de red.
"""

from unittest.mock import patch

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


def test_sin_token_no_op_false() -> None:
    """Dado gateway sin bot_token ni chat_id → no-op, retorna False."""
    gw = TelegramMailNotifierGateway()
    assert gw.notificar_oportunidad_email(_analisis(), _email()) is False


def test_envio_exitoso_payload_correcto() -> None:
    """Dado token/chat configurado y POST exitoso → True y payload con badges."""
    gw = TelegramMailNotifierGateway(
        bot_token="TOKEN_TEST", chat_id="CHAT_TEST"
    )
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        ok = gw.notificar_oportunidad_email(_analisis(), _email())

    assert ok is True
    assert mock_post.call_count == 1
    args, kwargs = mock_post.call_args
    assert "TOKEN_TEST" in args[0]
    assert kwargs["json"]["chat_id"] == "CHAT_TEST"
    payload = kwargs["json"]["text"]
    assert "OPORTUNIDAD B2B" in payload
    assert "Toyota Group" in payload
    assert "Buyer" in payload
    assert "95/100" in payload
    assert "ALTA" in payload
    assert "Realizado" in payload or "Responder" in payload or "siguiente" in payload


def test_error_de_red_retorna_false() -> None:
    """Dado fallo de red en requests → False sin propagar excepción."""
    gw = TelegramMailNotifierGateway(
        bot_token="TOKEN_TEST", chat_id="CHAT_TEST"
    )
    with patch("requests.post", side_effect=Exception("boom")):
        with pytest.raises(Exception):
            # El gateway debe capturar internamente y retornar False.
            pass
        assert gw.notificar_oportunidad_email(_analisis(), _email()) is False
