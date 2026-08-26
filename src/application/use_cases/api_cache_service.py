"""Servicio de caché para respuestas de APIs externas usando SQLAlchemy + MySQL."""

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from src.infrastructure.database.engine import get_session_factory
from src.infrastructure.database.models import ApiCacheEntry

# TTLs configurados por tipo de endpoint (en segundos).
# Confirmados y aprobados por el usuario el 2026-08-25.
CACHE_TTL: dict[str, int] = {
    "google_ads:campaign_performance": 4 * 3600,   # 4 horas
    "google_ads:search_terms_report":  12 * 3600,  # 12 horas
    "google_ads:daily_budget_pacing":  15 * 60,    # 15 minutos (monitoreo de presupuesto)
    "ga4:top_pages":                   3600,        # 1 hora
    "ga4:traffic_sources":             3600,        # 1 hora
    "ga4:conversions":                 3600,        # 1 hora
    "ga4:geo_traffic":                 3600,        # 1 hora
    "clarity:live_insights":           2 * 3600,   # 2 horas
    "clarity:dashboard_insights":      2 * 3600,   # 2 horas
}
DEFAULT_TTL: int = 3600  # 1 hora por defecto para claves no registradas


class ApiCacheService:
    """Gestiona la lectura y escritura de respuestas de APIs en la tabla api_cache de MySQL.

    Degrada elegantemente: si DATABASE_URL no está configurado, get() retorna None
    y set() es un no-op, permitiendo que el sistema funcione sin caché.
    """

    def get(self, key: str) -> Optional[Any]:
        """Recupera un valor de caché si existe y no está expirado.

        Args:
            key: Clave canónica de caché (ej. "google_ads:campaign_performance:days_7").

        Returns:
            El valor deserializado si hay hit válido, None en caso contrario.
        """
        factory = get_session_factory()
        if factory is None:
            return None
        now = datetime.utcnow()
        with factory() as session:
            entry: Optional[ApiCacheEntry] = (
                session.query(ApiCacheEntry)
                .filter(
                    ApiCacheEntry.cache_key == key,
                    ApiCacheEntry.expires_at > now,
                )
                .first()
            )
            if entry is not None:
                result: Any = json.loads(entry.response_json)
                return result
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Almacena un valor en caché con TTL resuelto automáticamente por prefijo de clave.

        Args:
            key: Clave canónica de caché.
            value: Valor serializable a JSON (usualmente dict[str, Any]).
            ttl_seconds: TTL explícito en segundos. Si es None, se resuelve por prefijo.
        """
        factory = get_session_factory()
        if factory is None:
            return
        ttl = ttl_seconds if ttl_seconds is not None else self._resolve_ttl(key)
        now = datetime.utcnow()
        expires = now + timedelta(seconds=ttl)
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        with factory() as session:
            entry = session.query(ApiCacheEntry).filter_by(cache_key=key).first()
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
        """Resuelve el TTL en segundos según el prefijo de la clave de caché.

        Args:
            key: Clave canónica de caché.

        Returns:
            TTL en segundos correspondiente al prefijo, o DEFAULT_TTL si no hay coincidencia.
        """
        for prefix, ttl in CACHE_TTL.items():
            if key.startswith(prefix):
                return ttl
        return DEFAULT_TTL
