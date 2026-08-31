"""Tests unitarios para el gateway de consumo de APIs de LLM (DeepSeek y AGY)."""

from src.adapters.gateways.api_usage_gateway import (
    APIUsageGateway,
    parse_tokens,
)


def test_parse_tokens_helper() -> None:
    """Valida la conversión de cadenas de tokens a enteros."""
    assert parse_tokens("72k") == 72000
    assert parse_tokens("1.5m") == 1500000
    assert parse_tokens("848") == 848
    assert parse_tokens("0") == 0
    assert parse_tokens("") == 0


def test_api_usage_gateway_deepseek_missing_key() -> None:
    """Si DEEPSEEK_API_KEY no está configurada, DeepSeek debe reportarse no disponible."""
    gateway = APIUsageGateway(deepseek_api_key=None)
    data = gateway.obtener_usage_consolidado()

    assert data["deepseek"]["is_available"] is False
    assert data["deepseek"]["balance"] == 0.0
    assert data["deepseek"]["currency"] == "USD"
    assert data["agy"]["input_tokens"] >= 0
    assert data["agy"]["output_tokens"] >= 0
    assert data["agy"]["cached_tokens"] >= 0


class MockCache:
    """Mock simple para ApiCacheGateway."""

    def __init__(self) -> None:
        self.store = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: any, ttl_seconds: int | None = None) -> None:
        self.store[key] = value


def test_api_usage_gateway_cache_consolidation() -> None:
    """Valida que los tokens locales guardados en cache se sumen al consolidado."""
    mock_cache = MockCache()
    gateway = APIUsageGateway(deepseek_api_key=None, cache=mock_cache)

    gateway.guardar_usage_local(
        input_tokens=1000, output_tokens=200, cached_tokens=5000
    )
    data = gateway.obtener_usage_consolidado()

    assert data["agy"]["input_tokens"] >= 1000
    assert data["agy"]["output_tokens"] >= 200
    assert data["agy"]["cached_tokens"] >= 5000
