"""Modelos ORM de SQLAlchemy para la capa de persistencia de datamaq-hub."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.engine import Base


class ApiCacheEntry(Base):
    """Registro de caché de respuestas de APIs externas (Google Ads, GA4, Clarity).

    Cada fila almacena la respuesta serializada en JSON de un endpoint externo,
    identificada por una clave canónica y con fecha de expiración configurable.
    """

    __tablename__ = "api_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    response_json: Mapped[str] = mapped_column(
        Text(length=16_777_215),  # MEDIUMTEXT — soporta JSONs grandes de GA4
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    def __repr__(self) -> str:
        return (
            f"<ApiCacheEntry key={self.cache_key!r} expires_at={self.expires_at!r}>"
        )
