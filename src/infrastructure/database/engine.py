"""Motor SQLAlchemy compartido para la base de datos de caché de APIs externas."""

from functools import lru_cache
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.infrastructure.pydantic.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos ORM de datamaq-hub."""


@lru_cache
def get_engine() -> Optional[Engine]:
    """Retorna el motor SQLAlchemy cacheado.

    Retorna None si DATABASE_URL no está configurado, permitiendo que el
    servicio opere sin caché (degradación elegante).
    """
    settings = get_settings()
    if not settings.database_url:
        return None
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )


def get_session_factory() -> Optional[sessionmaker[Session]]:
    """Retorna la fábrica de sesiones SQLAlchemy o None si la BD no está configurada."""
    engine = get_engine()
    if engine is None:
        return None
    return sessionmaker(bind=engine, expire_on_commit=False)
