"""Integration tests para las rutas de análisis de oportunidades B2B en correo."""

import pytest
from fastapi.testclient import TestClient

from src.adapters.controllers.dependencies import get_mail_analysis_controller
from src.domain.mail.entities import EmailDetail, EmailSummary, UnreadSummary
from src.infrastructure.fastapi.routes.mail_routes import (
    get_configured_mail_analysis_controller,
)
from src.infrastructure.fastapi.server import create_app

_CORREO = EmailDetail(
    uid="4821",
    remitente="Gurzale, Sol <sol.gurzale@jtekt.onmicrosoft.com>",
    destinatarios=["info@datamaq.com.ar"],
    asunto="RE: Proyecto automatización",
    fecha="2026-09-03T22:14:00-03:00",
    cuerpo_texto=(
        "Evaluando proveedores para la bajada de datos de las lineas de inyeccion "
        "y tiempos de ciclo de las inyectoras. Jefe de mantenimiento."
    ),
)


class _BuzonFalso:
    """Lector de correo mínimo que devuelve una única oportunidad comercial."""

    def get_folders(self) -> list[object]:
        return []

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[EmailSummary], int, int]:
        resumen = EmailSummary(
            uid=_CORREO.uid,
            remitente=_CORREO.remitente,
            asunto=_CORREO.asunto,
            snippet="Evaluando proveedores…",
        )
        return [resumen], 1, 1

    def get_message_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_html: bool = False,
        max_chars: int = 4000,
    ) -> EmailDetail | None:
        return _CORREO if uid == _CORREO.uid else None

    def get_unread_summary(
        self, folder: str = "INBOX", limit: int = 5, q: str | None = None
    ) -> UnreadSummary:
        return UnreadSummary(carpeta=folder, total_no_leidos=1)


class _CacheFalsa:
    def __init__(self) -> None:
        self.almacen: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self.almacen.get(key)

    def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        self.almacen[key] = value


class _NotificadorFalso:
    def __init__(self) -> None:
        self.enviadas: list[str] = []

    def notificar_oportunidad_email(self, analisis: object, email: object) -> bool:
        self.enviadas.append(getattr(analisis, "uid", ""))
        return True


@pytest.fixture
def notificador() -> _NotificadorFalso:
    return _NotificadorFalso()


@pytest.fixture
def analysis_client(notificador: _NotificadorFalso) -> TestClient:
    controller = get_mail_analysis_controller(
        gateway=_BuzonFalso(),  # type: ignore[arg-type]
        cache=_CacheFalsa(),  # type: ignore[arg-type]
        notifier=notificador,  # type: ignore[arg-type]
    )
    app = create_app()
    app.dependency_overrides[get_configured_mail_analysis_controller] = lambda: (
        controller
    )
    return TestClient(app)


def test_scan_detecta_oportunidad_y_notifica(
    analysis_client: TestClient, notificador: _NotificadorFalso
) -> None:
    response = analysis_client.post(
        "/api/v1/mail/analizar", json={"cuenta": "info@datamaq.com.ar", "limit": 5}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_escaneados"] == 1
    assert data["total_oportunidades"] == 1
    assert data["alertas_enviadas"] == 1
    assert notificador.enviadas == ["4821"]


def test_scan_deduplica_alertas_entre_corridas(
    analysis_client: TestClient, notificador: _NotificadorFalso
) -> None:
    """El cron corre cada pocos minutos: el mismo correo no debe alertar dos veces."""
    cuerpo = {"cuenta": "info@datamaq.com.ar", "limit": 5}
    analysis_client.post("/api/v1/mail/analizar", json=cuerpo)
    segunda = analysis_client.post("/api/v1/mail/analizar", json=cuerpo)

    data = segunda.json()["data"]
    assert data["total_oportunidades"] == 1
    assert data["alertas_enviadas"] == 0
    assert len(notificador.enviadas) == 1


def test_scan_puede_forzar_la_notificacion(
    analysis_client: TestClient, notificador: _NotificadorFalso
) -> None:
    cuerpo = {"cuenta": "info@datamaq.com.ar", "limit": 5}
    analysis_client.post("/api/v1/mail/analizar", json=cuerpo)
    analysis_client.post(
        "/api/v1/mail/analizar", json={**cuerpo, "forzar_notificacion": True}
    )

    assert len(notificador.enviadas) == 2


def test_analisis_individual_no_notifica(
    analysis_client: TestClient, notificador: _NotificadorFalso
) -> None:
    response = analysis_client.get(
        "/api/v1/mail/analizar/4821", params={"cuenta": "info@datamaq.com.ar"}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["categoria"] == "OPORTUNIDAD_COMERCIAL"
    assert data["prioridad"] == "ALTA"
    assert data["entidades"]["contacto_nombre"] == "Sol Gurzale"
    assert notificador.enviadas == []
