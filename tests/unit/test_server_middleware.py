"""Tests RED para middleware gzip, fallback de URL de BD y PRAGMA WAL (R-S1..R-S3)."""

from sqlalchemy import text

from src.adapters.gateways.api_cache_gateway import get_engine
from src.infrastructure.fastapi.server import _resolve_database_url, create_app


def test_gzip_middleware_registered() -> None:
    """R-S1: create_app registra GZipMiddleware con minimum_size=1000."""
    app = create_app()
    gzip_mws = [m for m in app.user_middleware if m.cls.__name__ == "GZipMiddleware"]
    assert len(gzip_mws) == 1
    assert gzip_mws[0].kwargs.get("minimum_size") == 1000


def test_resolve_database_url_fallback() -> None:
    """R-S2: URL vacía → SQLite file; URL real se conserva."""
    assert _resolve_database_url("") == "sqlite:///data/datamaq_hub.db"
    mysql_url = "mysql+pymysql://user:pass@host/db"
    assert _resolve_database_url(mysql_url) == mysql_url


def test_sqlite_engine_enables_wal(tmp_path) -> None:
    """R-S3: engine SQLite file activa PRAGMA journal_mode=WAL."""
    db_file = tmp_path / "cache.db"
    engine = get_engine(f"sqlite:///{db_file}")
    assert engine is not None
    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert mode == "wal"
