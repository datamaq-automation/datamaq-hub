"""Gateway de caché persistente para APIs externas (SQLAlchemy + MySQL).

Encapsula el ORM de SQLAlchemy y el motor de BD directamente en la capa de
adapters (mismo patrón que ``pdfplumber_extractor_gateway``), respetando la
Regla Sagrada 1: los adapters nunca importan ``src.infrastructure``.

La configuración (``database_url`` y ``ttl_by_prefix``) se inyecta por
constructor desde la capa más externa (FastMCP / FastAPI startup).
"""

import json
from datetime import datetime, timedelta, timezone
from functools import cache
from typing import Any

from sqlalchemy import DateTime, Engine, Integer, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.domain.cache.ports import ApiCachePort

# TTLs de fallback por prefijo de clave (segundos), confirmados el 2026-08-25.
# Sobreescribibles vía ``ttl_by_prefix`` (Settings.cache_ttls desde .env).
CACHE_TTL: dict[str, int] = {
    "google_ads:campaign_performance": 4 * 3600,  # 4 horas
    "google_ads:search_terms_report": 12 * 3600,  # 12 horas
    "google_ads:daily_budget_pacing": 15 * 60,  # 15 minutos
    "ga4:top_pages": 3600,  # 1 hora
    "ga4:traffic_sources": 3600,  # 1 hora
    "ga4:conversions": 3600,  # 1 hora
    "ga4:geo_traffic": 3600,  # 1 hora
    "clarity:live_insights": 2 * 3600,  # 2 horas
    "clarity:dashboard_insights": 2 * 3600,  # 2 horas
}
DEFAULT_TTL: int = 3600  # 1 hora para claves sin prefijo registrado


class Base(DeclarativeBase):
    """Base declarativa para los modelos ORM de la caché."""


class ApiCacheEntry(Base):
    """Registro de caché de una respuesta de API externa serializada en JSON."""

    __tablename__ = "api_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    response_json: Mapped[str] = mapped_column(
        Text(length=16_777_215),  # MEDIUMTEXT — soporta JSONs grandes de GA4
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


def _utcnow() -> datetime:
    """Retorna el instante actual en UTC como datetime naive (compatible MySQL/SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@cache
def get_engine(database_url: str | None) -> Engine | None:
    """Retorna el motor SQLAlchemy cacheado por URL. None si no hay BD configurada."""
    if not database_url:
        return None
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )


def get_session_factory(
    database_url: str | None,
) -> sessionmaker[Session] | None:
    """Retorna la fábrica de sesiones o None si la BD no está configurada."""
    engine = get_engine(database_url)
    if engine is None:
        return None
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(database_url: str | None) -> None:
    """Crea las tablas si no existen. Idempotente; no-op sin BD configurada."""
    engine = get_engine(database_url)
    if engine is not None:
        Base.metadata.create_all(engine)


class ApiCacheGateway(ApiCachePort):
    """Implementación de ``ApiCachePort`` sobre SQLAlchemy (MySQL/schema datamaq_hub)."""

    def __init__(
        self,
        database_url: str | None = None,
        ttl_by_prefix: dict[str, int] | None = None,
    ) -> None:
        self._database_url = database_url
        # Merge: lo configurado sobreescribe; lo ausente conserva el default aprobado.
        self._ttl_by_prefix: dict[str, int] = {
            **CACHE_TTL,
            **(ttl_by_prefix or {}),
        }

    def get(self, key: str) -> Any | None:
        """Recupera un valor si hay entrada vigente. None en miss, expirado o sin BD."""
        factory = get_session_factory(self._database_url)
        if factory is None:
            return None
        with factory() as session:
            entry = session.execute(
                select(ApiCacheEntry).where(ApiCacheEntry.cache_key == key)
            ).scalar_one_or_none()
        if entry is None:
            return None
        if entry.expires_at <= _utcnow():
            return None
        return json.loads(entry.response_json)

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Persiste ``value`` con TTL resuelto por prefijo. No-op sin BD."""
        factory = get_session_factory(self._database_url)
        if factory is None:
            return
        ttl = ttl_seconds if ttl_seconds is not None else self._resolve_ttl(key)
        now = _utcnow()
        expires = now + timedelta(seconds=ttl)
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        with factory() as session:
            entry = session.execute(
                select(ApiCacheEntry).where(ApiCacheEntry.cache_key == key)
            ).scalar_one_or_none()
            if entry is not None:
                entry.response_json = serialized
                entry.created_at = now
                entry.expires_at = expires
            else:
                session.add(
                    ApiCacheEntry(
                        cache_key=key,
                        response_json=serialized,
                        created_at=now,
                        expires_at=expires,
                    )
                )
            session.commit()

    def _resolve_ttl(self, key: str) -> int:
        """Resuelve el TTL en segundos según el prefijo de la clave."""
        for prefix, ttl in self._ttl_by_prefix.items():
            if key.startswith(prefix):
                return ttl
        return DEFAULT_TTL
