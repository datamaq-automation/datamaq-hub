"""Tests unitarios del gateway de caché persistente (SQLite en memoria, sin MySQL)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import delete, select

from src.adapters.gateways.api_cache_gateway import (
    DEFAULT_TTL,
    ApiCacheEntry,
    ApiCacheGateway,
    get_engine,
    get_session_factory,
    init_db,
    resolve_database_url,
)

TEST_URL = "sqlite:///:memory:"


def _clear_table() -> None:
    """Borra todas las filas de api_cache entre tests (BD compartida en memoria)."""
    engine = get_engine(TEST_URL)
    if engine is None:
        return
    with engine.connect() as conn:
        conn.execute(delete(ApiCacheEntry))
        conn.commit()


@pytest.fixture()
def gateway() -> Iterator[ApiCacheGateway]:
    """Gateway respaldado por SQLite en memoria con la tabla inicializada."""
    init_db(TEST_URL)
    gw = ApiCacheGateway(database_url=TEST_URL)
    yield gw
    _clear_table()


def test_get_returns_none_without_db_on_miss() -> None:
    """R1: sin DATABASE_URL y sin set previo, get() retorna None sin excepción."""
    gw = ApiCacheGateway(database_url=None)
    assert gw.get("cualquier:clave") is None


def test_in_memory_fallback_without_db() -> None:
    """R2: sin DATABASE_URL, set() y get() operan en memoria con TTL."""
    gw = ApiCacheGateway(database_url=None)
    gw.set("cualquier:clave", {"a": 1})
    assert gw.get("cualquier:clave") == {"a": 1}

    # Expiración en memoria
    gw.set("clave:expirada", {"b": 2}, ttl_seconds=-1)
    assert gw.get("clave:expirada") is None


def test_invalid_database_url_fallback_gracefully() -> None:
    """R2b: ante DATABASE_URL rota, opera en memoria sin arrojar excepciones."""
    gw = ApiCacheGateway(
        database_url="mysql+pymysql://invalid:fake@127.0.0.1:9999/nonexistent"
    )
    gw.set("clave:resiliencia", {"ok": True})
    assert gw.get("clave:resiliencia") == {"ok": True}


def test_get_returns_none_on_miss(gateway: ApiCacheGateway) -> None:
    """R3: tabla vacía, get() de clave inexistente retorna None."""
    assert gateway.get("clave:inexistente") is None


def test_get_returns_value_on_hit(gateway: ApiCacheGateway) -> None:
    """R4: entrada vigente, get() retorna el valor deserializado."""
    key = "ga4:top_pages:days_7:limit_10:segment_all"
    value = {"status": "success", "rows": [{"pagePath": "/"}]}
    gateway.set(key, value)
    assert gateway.get(key) == value


def test_get_returns_none_on_expired(gateway: ApiCacheGateway) -> None:
    """R5: entrada expirada, get() retorna None."""
    gateway.set("clave:expirada", {"a": 1}, ttl_seconds=-1)
    assert gateway.get("clave:expirada") is None


def test_set_creates_new_entry(gateway: ApiCacheGateway) -> None:
    """R6: set() sobre clave inexistente inserta una fila con expiración futura."""
    gateway.set("google_ads:daily_budget_pacing", {"spent_ars": 10.0})
    factory = get_session_factory(TEST_URL)
    assert factory is not None
    with factory() as session:
        entry = session.execute(select(ApiCacheEntry)).scalar_one()
    assert entry.cache_key == "google_ads:daily_budget_pacing"
    assert entry.expires_at > entry.created_at


def test_set_updates_existing_entry(gateway: ApiCacheGateway) -> None:
    """R7: set() sobre clave existente actualiza sin duplicar la fila."""
    gateway.set("clave:repetida", {"v": 1})
    gateway.set("clave:repetida", {"v": 2})
    assert gateway.get("clave:repetida") == {"v": 2}
    factory = get_session_factory(TEST_URL)
    assert factory is not None
    with factory() as session:
        rows = (
            session.execute(
                select(ApiCacheEntry).where(ApiCacheEntry.cache_key == "clave:repetida")
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1


@pytest.mark.parametrize(
    ("key", "expected_ttl"),
    [
        ("google_ads:campaign_performance:days_7", 4 * 3600),
        ("google_ads:search_terms_report:days_7:limit_20", 12 * 3600),
        ("google_ads:daily_budget_pacing", 15 * 60),
        ("ga4:top_pages:days_7:limit_10:segment_all", 3600),
        ("ga4:traffic_sources:days_7:limit_10", 3600),
        ("ga4:conversions:days_7", 3600),
        ("ga4:geo_traffic:days_7:limit_15", 3600),
        ("clarity:live_insights", 2 * 3600),
        ("clarity:dashboard_insights:days_3", 2 * 3600),
    ],
)
def test_resolve_ttl_by_prefix(
    gateway: ApiCacheGateway, key: str, expected_ttl: int
) -> None:
    """R8: cada prefijo conocido resuelve su TTL aprobado."""
    assert gateway._resolve_ttl(key) == expected_ttl


def test_resolve_ttl_default(gateway: ApiCacheGateway) -> None:
    """R9: clave sin prefijo registrado usa DEFAULT_TTL (3600)."""
    assert gateway._resolve_ttl("prefijo:desconocido") == DEFAULT_TTL


def test_timestamps_persisted_as_naive_utc(gateway: ApiCacheGateway) -> None:
    """R10: los timestamps persisten como naive UTC (compatible MySQL/SQLite)."""
    gateway.set("clave:utc", {"a": 1})
    factory = get_session_factory(TEST_URL)
    assert factory is not None
    with factory() as session:
        entry = session.execute(
            select(ApiCacheEntry).where(ApiCacheEntry.cache_key == "clave:utc")
        ).scalar_one()
    assert entry.created_at.tzinfo is None
    assert entry.expires_at.tzinfo is None


def test_resolve_ttl_partial_override() -> None:
    """R13: override parcial — lo configurado manda, lo ausente conserva default."""
    gw = ApiCacheGateway(
        database_url=None,
        ttl_by_prefix={"google_ads:daily_budget_pacing": 30},
    )
    assert gw._resolve_ttl("google_ads:daily_budget_pacing") == 30
    assert gw._resolve_ttl("google_ads:campaign_performance:days_7") == 4 * 3600


def test_resolve_ttl_defaults_without_args() -> None:
    """R14: constructor sin ttl_by_prefix usa las constantes aprobadas."""
    gw = ApiCacheGateway(database_url=None)
    assert gw._resolve_ttl("google_ads:campaign_performance:days_7") == 4 * 3600
    assert gw._resolve_ttl("clarity:live_insights") == 2 * 3600


def test_mail_ttl_registered_by_prefix() -> None:
    """Contratos C6: los prefijos de mail resuelven su TTL desde constantes aprobadas."""
    gw = ApiCacheGateway(database_url=None)
    assert gw._resolve_ttl("mail:unread_summary:abc:INBOX") == 60
    assert gw._resolve_ttl("mail:folders:abc") == 5 * 60


def test_resolve_database_url_fallback_sqlite() -> None:
    """Regresión: DATABASE_URL vacío resuelve al archivo SQLite persistente."""
    assert resolve_database_url("") == "sqlite:///data/datamaq_hub.db"
    assert resolve_database_url(None) == "sqlite:///data/datamaq_hub.db"
    assert resolve_database_url("mysql+pymysql://db") == "mysql+pymysql://db"
