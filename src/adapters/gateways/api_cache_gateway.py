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

from sqlalchemy import DateTime, Engine, Integer, Text, create_engine, event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.domain.cache.ports import ApiCachePort
from src.domain.common.ports import LoggerPort, NullLogger

# Archivo SQLite de respaldo cuando DATABASE_URL está vacío (decisión de la
# capa gateway; evita cachear solo en memoria L1 y perder la caché entre procesos).
DEFAULT_SQLITE_FILE = "sqlite:///data/datamaq_hub.db"


def resolve_database_url(raw: str | None) -> str:
    """Resuelve la URL de BD; usa el fallback SQLite file cuando está vacía o nula."""
    return raw or DEFAULT_SQLITE_FILE


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
    "mail:unread_summary": 60,  # 1 minuto
    "mail:folders": 5 * 60,  # 5 minutos
    "search_console:top_queries": 6 * 3600,  # 6 horas
    "search_console:top_pages": 6 * 3600,  # 6 horas
    "search_console:page_queries": 6 * 3600,  # 6 horas
    "search_console:performance": 6 * 3600,  # 6 horas
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


def _habilitar_wal(engine: Engine) -> None:
    """Activa PRAGMA journal_mode=WAL en cada conexión de un engine SQLite file."""

    @event.listens_for(engine, "connect")
    def _set_wal(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor: Any = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


@cache
def get_engine(database_url: str | None) -> Engine | None:
    """Retorna el motor SQLAlchemy cacheado por URL. None si no hay BD configurada o si falla la conexión."""
    if not database_url:
        return None
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        if database_url.startswith("sqlite") and ":memory:" not in database_url:
            _habilitar_wal(engine)
        return engine
    except (SQLAlchemyError, OSError, ValueError, RuntimeError):
        return None


def get_session_factory(
    database_url: str | None,
    logger: LoggerPort | None = None,
) -> sessionmaker[Session] | None:
    """Retorna la fábrica de sesiones o None si la BD no está configurada o falló."""
    logger = logger or NullLogger()
    engine = get_engine(database_url)
    if engine is None:
        return None
    try:
        return sessionmaker(bind=engine, expire_on_commit=False)
    except (SQLAlchemyError, OSError, ValueError, RuntimeError) as exc:
        logger.debug("ApiCache: No se pudo crear sessionmaker: %s", exc)
        return None


def init_db(database_url: str | None, logger: LoggerPort | None = None) -> None:
    """Crea las tablas si no existen. Idempotente; no-op sin BD configurada o ante error de conexión."""
    logger = logger or NullLogger()
    engine = get_engine(database_url)
    if engine is not None:
        try:
            Base.metadata.create_all(engine)
        except (SQLAlchemyError, OSError, ValueError, RuntimeError) as exc:
            logger.debug("ApiCache: No se pudo inicializar BD: %s", exc)


class ApiCacheGateway(ApiCachePort):
    """Implementación de ``ApiCachePort`` sobre SQLAlchemy con fallback automático en memoria."""

    def __init__(
        self,
        database_url: str | None = None,
        ttl_by_prefix: dict[str, int] | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        self._database_url = database_url
        self._logger = logger or NullLogger()
        self._memory_cache: dict[str, tuple[datetime, Any]] = {}
        # Merge: lo configurado sobreescribe; lo ausente conserva el default aprobado.
        self._ttl_by_prefix: dict[str, int] = {
            **CACHE_TTL,
            **(ttl_by_prefix or {}),
        }

    def get(self, key: str) -> Any | None:
        """Recupera un valor si hay entrada vigente (BD o memoria). None en miss o expirado."""
        # 1. Intentar recuperación desde Base de Datos si está configurada
        try:
            factory = get_session_factory(self._database_url, self._logger)
            if factory is not None:
                with factory() as session:
                    entry = session.execute(
                        select(ApiCacheEntry).where(ApiCacheEntry.cache_key == key)
                    ).scalar_one_or_none()
                if entry is not None:
                    if entry.expires_at <= _utcnow():
                        return None
                    return json.loads(entry.response_json)
        except (SQLAlchemyError, OSError, ValueError, RuntimeError) as exc:
            self._logger.debug("ApiCache: Error recuperando '%s' de BD: %s", key, exc)

        # 2. Fallback / L1: recuperar de la caché en memoria del proceso
        if key in self._memory_cache:
            expires_at, mem_val = self._memory_cache[key]
            if expires_at > _utcnow():
                return mem_val
            del self._memory_cache[key]

        return None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Persiste ``value`` en BD y memoria con TTL resuelto por prefijo."""
        ttl = ttl_seconds if ttl_seconds is not None else self._resolve_ttl(key)
        now = _utcnow()
        expires = now + timedelta(seconds=ttl)

        # 1. Guardar siempre en memoria (L1 / fallback garantizado)
        self._memory_cache[key] = (expires, value)

        # 2. Persistir en Base de Datos si está disponible
        try:
            factory = get_session_factory(self._database_url, self._logger)
            if factory is not None:
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
        except (SQLAlchemyError, OSError, ValueError, RuntimeError) as exc:
            self._logger.debug("ApiCache: Error persistiendo '%s' en BD: %s", key, exc)

    def _resolve_ttl(self, key: str) -> int:
        """Resuelve el TTL en segundos según el prefijo de la clave."""
        for prefix, ttl in self._ttl_by_prefix.items():
            if key.startswith(prefix):
                return ttl
        return DEFAULT_TTL
