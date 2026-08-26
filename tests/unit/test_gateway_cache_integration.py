"""Tests de integración de la caché en los gateways de APIs externas (FakeCache)."""

from typing import Any

import pytest

from src.adapters.gateways.clarity_gateway import ClarityGateway
from src.adapters.gateways.ga4_gateway import GA4Gateway
from src.adapters.gateways.google_ads_gateway import GoogleAdsGateway
from src.domain.cache.ports import ApiCachePort


class FakeCache(ApiCachePort):
    """Fake en memoria para verificar la interacción caché/gateway sin BD real."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self.set_calls: int = 0

    def get(self, key: str) -> Any | None:
        return self._store.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self.set_calls += 1
        self._store[key] = value


def test_ga4_top_pages_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """R11: GA4 consulta la API una sola vez; la segunda llamada sirve caché."""
    cache = FakeCache()
    gateway = GA4Gateway("prop-123", "/creds.json", cache=cache)
    calls: list[int] = []

    def fake_report(*args: object, **kwargs: object) -> dict[str, Any]:
        calls.append(1)
        return {
            "status": "success",
            "rows": [
                {
                    "pagePath": "/",
                    "pageTitle": "Home",
                    "screenPageViews": "10",
                    "activeUsers": "5",
                }
            ],
        }

    monkeypatch.setattr(
        "src.adapters.gateways.ga4_gateway._run_ga4_report", fake_report
    )
    first = gateway.get_top_pages()
    second = gateway.get_top_pages()
    assert len(calls) == 1
    assert cache.set_calls == 1
    assert first == second


class _FakeAdsService:
    def __init__(self) -> None:
        self.search_calls: int = 0

    def search(self, customer_id: str = "", query: str = "") -> Any:
        self.search_calls += 1
        return iter([])


class _FakeAdsClient:
    def __init__(self, service: _FakeAdsService) -> None:
        self._service = service

    def get_service(self, name: str) -> _FakeAdsService:
        return self._service


def test_google_ads_budget_pacing_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """R11: Google Ads consulta la API una sola vez; la segunda sirve caché."""
    cache = FakeCache()
    gateway = GoogleAdsGateway("dt", "cid", "cs", "rt", "cust-1", cache=cache)
    monkeypatch.setattr(gateway, "get_status", lambda: {"status": "ready"})

    service = _FakeAdsService()

    def fake_client(*args: object, **kwargs: object) -> _FakeAdsClient:
        return _FakeAdsClient(service)

    monkeypatch.setattr(
        "src.adapters.gateways.google_ads_gateway._get_google_ads_client",
        fake_client,
    )
    first = gateway.get_daily_budget_pacing()
    second = gateway.get_daily_budget_pacing()
    assert service.search_calls == 1
    assert cache.set_calls == 1
    assert first == second


def test_clarity_live_insights_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """R11: Clarity consulta la API una sola vez; la segunda sirve caché."""
    cache = FakeCache()
    gateway = ClarityGateway("cid", "token", cache=cache)
    calls: list[int] = []

    def fake_request(*args: object, **kwargs: object) -> dict[str, Any]:
        calls.append(1)
        return {"status": "success", "data": {"active_users": 3}}

    monkeypatch.setattr(
        "src.adapters.gateways.clarity_gateway._clarity_api_request", fake_request
    )
    first = gateway.get_live_insights()
    second = gateway.get_live_insights()
    assert len(calls) == 1
    assert cache.set_calls == 1
    assert first == second
