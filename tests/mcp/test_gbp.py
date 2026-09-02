"""Tests unitarios para el servidor FastMCP de Google Business Profile (DataMaq)."""

import json
import urllib.error
from io import BytesIO
from typing import Any

import pytest

import src.infrastructure.fastmcp.gbp as gbp_mcp
from src.adapters.gateways.gbp_gateway import (
    APPROVAL_GUIDE,
    GoogleBusinessProfileGateway,
    _estrellas_a_entero,
    _http_request,
)
from src.application.use_cases.publicar_en_ficha_google import (
    PublicarEnFichaGoogleUseCase,
)

CREDENCIALES: dict[str, str] = {
    "client_id": "id-falso",
    "client_secret": "secreto-falso",
    "refresh_token": "refresh-falso",
    "account_id": "123",
    "location_id": "456",
}


def _gateway(**overrides: Any) -> GoogleBusinessProfileGateway:
    """Construye un gateway con credenciales de prueba y sin caché persistente."""
    datos = {**CREDENCIALES, **overrides}
    return GoogleBusinessProfileGateway(**datos)


class _CacheFalsa:
    """Caché en memoria que cumple ApiCachePort sin tocar la base de datos."""

    def __init__(self) -> None:
        self.valores: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        return self.valores.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        if ttl_seconds == 0:
            self.valores.pop(key, None)
        else:
            self.valores[key] = value


# --------------------------------------------------------------- degradación


def test_gbp_sin_credenciales_degrada() -> None:
    gateway = _gateway(client_id="", client_secret="", refresh_token="")
    for resultado in (
        gateway.get_status(),
        gateway.get_location_info(),
        gateway.get_performance(),
        gateway.get_search_keywords(),
        gateway.get_reviews(),
    ):
        assert resultado["status"] == "missing_credentials"
        assert "GBP_REFRESH_TOKEN" in resultado["setup_guide"]


def test_faltan_credenciales_gana_sobre_falta_de_ficha() -> None:
    """Sin credenciales no hay forma de resolver la ficha: el diagnóstico correcto es el de OAuth."""
    gateway = _gateway(
        client_id="", client_secret="", refresh_token="", account_id="", location_id=""
    )
    assert gateway.get_performance()["status"] == "missing_credentials"
    assert gateway.get_reviews()["status"] == "missing_credentials"


def test_gbp_sin_location_configurada() -> None:
    gateway = _gateway(location_id="")
    resultado = gateway.get_performance()
    assert resultado["status"] == "missing_location"


def test_gbp_reviews_sin_account_configurada() -> None:
    gateway = _gateway(account_id="")
    resultado = gateway.get_reviews()
    assert resultado["status"] == "missing_account"


def test_gbp_tools_sin_credenciales(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gbp_mcp,
        "_gateway",
        _gateway(client_id="", client_secret="", refresh_token=""),
    )
    assert gbp_mcp.get_gbp_status()["status"] == "missing_credentials"
    assert gbp_mcp.get_gbp_performance()["status"] == "missing_credentials"


# ------------------------------------------------------- traducción de errores


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://businessprofileperformance.googleapis.com",
        code=code,
        msg="error",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(b'{"error": "quota"}'),
    )


def test_http_429_se_traduce_a_api_not_approved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _falla(*_args: Any, **_kwargs: Any) -> None:
        raise _http_error(429)

    monkeypatch.setattr("urllib.request.urlopen", _falla)
    resultado = _http_request("https://ejemplo", "token")
    assert resultado["status"] == "api_not_approved"
    assert resultado["setup_guide"] == APPROVAL_GUIDE


def test_http_403_se_traduce_a_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _falla(*_args: Any, **_kwargs: Any) -> None:
        raise _http_error(403)

    monkeypatch.setattr("urllib.request.urlopen", _falla)
    assert _http_request("https://ejemplo", "token")["status"] == "auth_error"


def test_estrellas_a_entero() -> None:
    assert _estrellas_a_entero("FIVE") == 5
    assert _estrellas_a_entero("one") == 1
    assert _estrellas_a_entero("STAR_RATING_UNSPECIFIED") == 0


# ----------------------------------------------------------- parseo de lectura


def test_performance_aplana_la_serie(monkeypatch: pytest.MonkeyPatch) -> None:
    respuesta = {
        "status": "success",
        "data": {
            "multiDailyMetricTimeSeries": [
                {
                    "dailyMetricTimeSeries": [
                        {
                            "dailyMetric": "WEBSITE_CLICKS",
                            "timeSeries": {
                                "datedValues": [
                                    {
                                        "date": {"year": 2026, "month": 8, "day": 3},
                                        "value": "7",
                                    },
                                    # Google omite 'value' cuando el día es 0.
                                    {"date": {"year": 2026, "month": 8, "day": 4}},
                                ]
                            },
                        }
                    ]
                }
            ]
        },
    }
    gateway = _gateway(cache=_CacheFalsa())
    monkeypatch.setattr(gateway, "_pedir", lambda *a, **k: respuesta)

    resultado = gateway.get_performance(days=2)
    assert resultado["status"] == "success"
    assert resultado["metricas"][0] == {
        "fecha": "2026-08-03",
        "metrica": "WEBSITE_CLICKS",
        "valor": 7,
    }
    assert resultado["metricas"][1]["valor"] == 0


def test_reviews_marca_las_no_respondidas(monkeypatch: pytest.MonkeyPatch) -> None:
    respuesta = {
        "status": "success",
        "data": {
            "averageRating": 4.5,
            "totalReviewCount": 2,
            "reviews": [
                {
                    "reviewId": "r1",
                    "reviewer": {"displayName": "Planta A"},
                    "starRating": "FIVE",
                    "comment": "Excelente",
                    "updateTime": "2026-08-01T10:00:00Z",
                    "reviewReply": {"comment": "Gracias"},
                },
                {
                    "reviewId": "r2",
                    "reviewer": {"displayName": "Planta B"},
                    "starRating": "FOUR",
                    "comment": "Buen trabajo",
                    "updateTime": "2026-08-02T10:00:00Z",
                },
            ],
        },
    }
    gateway = _gateway(cache=_CacheFalsa())
    monkeypatch.setattr(gateway, "_pedir", lambda *a, **k: respuesta)

    resultado = gateway.get_reviews()
    assert resultado["rating_promedio"] == 4.5
    assert resultado["resenas"][0]["tiene_respuesta"] is True
    assert resultado["resenas"][1]["tiene_respuesta"] is False
    assert resultado["resenas"][1]["estrellas"] == 4


def test_search_keywords_distingue_umbral(monkeypatch: pytest.MonkeyPatch) -> None:
    respuesta = {
        "status": "success",
        "data": {
            "searchKeywordsCounts": [
                {
                    "searchKeyword": "medicion de energia pilar",
                    "insightsValue": {"value": "31"},
                },
                {
                    "searchKeyword": "datamaq",
                    "insightsValue": {"threshold": "15"},
                },
            ]
        },
    }
    gateway = _gateway(cache=_CacheFalsa())
    monkeypatch.setattr(gateway, "_pedir", lambda *a, **k: respuesta)

    resultado = gateway.get_search_keywords()
    assert resultado["terminos"][0] == {
        "termino": "medicion de energia pilar",
        "impresiones": 31,
        "es_umbral": False,
    }
    assert resultado["terminos"][1]["es_umbral"] is True


# ---------------------------------------------------------------- escrituras


class _PuertoFalso:
    """Puerto de GBP que registra las escrituras sin salir a la red."""

    def __init__(self, resenas: list[dict[str, Any]] | None = None) -> None:
        self.resenas = resenas if resenas is not None else []
        self.posts_creados: list[dict[str, Any]] = []
        self.respuestas: list[dict[str, Any]] = []

    def get_reviews(self, limit: int = 20) -> dict[str, Any]:
        return {"status": "success", "resenas": self.resenas}

    def create_post(
        self,
        summary: str,
        cta_url: str,
        cta_type: str = "LEARN_MORE",
        schedule_time: str | None = None,
    ) -> dict[str, Any]:
        self.posts_creados.append({"summary": summary, "cta_url": cta_url})
        return {"status": "success", "post_name": "localPosts/1"}

    def reply_to_review(
        self, review_id: str, comment: str, overwrite: bool = False
    ) -> dict[str, Any]:
        self.respuestas.append({"review_id": review_id, "comment": comment})
        return {"status": "success", "review_id": review_id}


URL_VALIDA = "https://datamaq.com.ar/guias/x?utm_source=google&utm_campaign=gbp"


def test_publicar_rechaza_url_sin_utm() -> None:
    puerto = _PuertoFalso()
    caso = PublicarEnFichaGoogleUseCase(gbp_port=puerto)

    from src.application.dtos.analytics_dtos import GbpPostRequestDTO

    resultado = caso.publicar(
        GbpPostRequestDTO(summary="Nota", cta_url="https://datamaq.com.ar/guias/x")
    )
    assert resultado["status"] == "rejected"
    assert "utm_campaign=gbp" in resultado["message"]
    assert puerto.posts_creados == []


def test_publicar_rechaza_dominio_ajeno() -> None:
    puerto = _PuertoFalso()
    caso = PublicarEnFichaGoogleUseCase(gbp_port=puerto)

    from src.application.dtos.analytics_dtos import GbpPostRequestDTO

    resultado = caso.publicar(
        GbpPostRequestDTO(
            summary="Nota", cta_url="https://otrositio.com/x?utm_campaign=gbp"
        )
    )
    assert resultado["status"] == "rejected"
    assert puerto.posts_creados == []


def test_publicar_acepta_url_valida() -> None:
    puerto = _PuertoFalso()
    caso = PublicarEnFichaGoogleUseCase(gbp_port=puerto)

    from src.application.dtos.analytics_dtos import GbpPostRequestDTO

    resultado = caso.publicar(
        GbpPostRequestDTO(summary="Nota técnica", cta_url=URL_VALIDA)
    )
    assert resultado["status"] == "success"
    assert len(puerto.posts_creados) == 1


def test_responder_resena_no_pisa_respuesta_existente() -> None:
    puerto = _PuertoFalso(
        resenas=[{"review_id": "r1", "tiene_respuesta": True}],
    )
    caso = PublicarEnFichaGoogleUseCase(gbp_port=puerto)

    from src.application.dtos.analytics_dtos import GbpReviewReplyRequestDTO

    resultado = caso.responder_resena(
        GbpReviewReplyRequestDTO(review_id="r1", comment="Gracias")
    )
    assert resultado["status"] == "rejected"
    assert "overwrite=True" in resultado["message"]
    assert puerto.respuestas == []


def test_responder_resena_con_overwrite_explicito() -> None:
    puerto = _PuertoFalso(resenas=[{"review_id": "r1", "tiene_respuesta": True}])
    caso = PublicarEnFichaGoogleUseCase(gbp_port=puerto)

    from src.application.dtos.analytics_dtos import GbpReviewReplyRequestDTO

    resultado = caso.responder_resena(
        GbpReviewReplyRequestDTO(review_id="r1", comment="Gracias", overwrite=True)
    )
    assert resultado["status"] == "success"
    assert len(puerto.respuestas) == 1


def test_responder_resena_inexistente() -> None:
    puerto = _PuertoFalso(resenas=[{"review_id": "r1", "tiene_respuesta": False}])
    caso = PublicarEnFichaGoogleUseCase(gbp_port=puerto)

    from src.application.dtos.analytics_dtos import GbpReviewReplyRequestDTO

    resultado = caso.responder_resena(
        GbpReviewReplyRequestDTO(review_id="r99", comment="Gracias")
    )
    assert resultado["status"] == "not_found"
    assert puerto.respuestas == []


def test_responder_resena_invalida_la_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = _CacheFalsa()
    gateway = _gateway(cache=cache)
    clave = "gbp:reviews:locations/456:limit_20"
    cache.valores[clave] = {"status": "success", "resenas": []}
    gateway._claves_cacheadas.add(clave)

    monkeypatch.setattr(
        gateway, "_pedir", lambda *a, **k: {"status": "success", "data": {}}
    )
    gateway.reply_to_review(review_id="r1", comment="Gracias")

    assert clave not in cache.valores


def test_post_serializa_cuerpo_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """El cuerpo POST debe viajar como JSON con el CTA declarado."""
    capturado: dict[str, Any] = {}

    def _pedir(url: str, method: str = "GET", body: Any = None) -> dict[str, Any]:
        capturado["url"] = url
        capturado["method"] = method
        capturado["body"] = body
        return {"status": "success", "data": {"name": "localPosts/9"}}

    gateway = _gateway(cache=_CacheFalsa())
    monkeypatch.setattr(gateway, "_pedir", _pedir)

    gateway.create_post(
        summary="Hola", cta_url=URL_VALIDA, schedule_time="2026-09-15T09:00:00Z"
    )

    assert capturado["method"] == "POST"
    assert capturado["url"].endswith("/accounts/123/locations/456/localPosts")
    assert capturado["body"]["callToAction"]["url"] == URL_VALIDA
    assert capturado["body"]["scheduledTime"] == "2026-09-15T09:00:00Z"
    assert json.dumps(capturado["body"])
