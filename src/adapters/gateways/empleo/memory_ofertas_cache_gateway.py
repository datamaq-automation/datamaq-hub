"""In-memory cache gateway for empleo domain."""

import time

from src.domain.empleo.entities import OfertaLaboral
from src.domain.empleo.ports import OfertasCachePort


class MemoryOfertasCacheGateway(OfertasCachePort):
    """Implementación de caché en memoria con TTL para ofertas laborales."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, list[OfertaLaboral]]] = {}

    def obtener_ofertas(self, cache_key: str) -> list[OfertaLaboral] | None:
        """Obtiene ofertas si la clave existe y no ha expirado."""
        if cache_key not in self._store:
            return None
        expires_at, ofertas = self._store[cache_key]
        if time.time() > expires_at:
            del self._store[cache_key]
            return None
        return list(ofertas)

    def guardar_ofertas(
        self,
        cache_key: str,
        ofertas: list[OfertaLaboral],
        ttl_segundos: int = 3600,
    ) -> None:
        """Almacena ofertas asociadas a la clave con un TTL en segundos."""
        expires_at = time.time() + ttl_segundos
        self._store[cache_key] = (expires_at, list(ofertas))
