"""Puertos de la temática de caché de APIs externas (dominio puro).

Define la abstracción que consumen los gateways de Google Ads, GA4 y Clarity
sin acoplarse a la persistencia concreta (SQLAlchemy/MySQL).
"""

from abc import ABC, abstractmethod
from typing import Any


class ApiCachePort(ABC):
    """Contrato de caché de respuestas de APIs externas.

    Implementaciones concretas viven en adapters/gateways (ej. ApiCacheGateway).
    """

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Retorna el valor deserializado si hay entrada vigente.

        Retorna None en caso de miss, entrada expirada o ausencia de BD.
        """

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Persiste ``value`` serializado a JSON.

        Si ``ttl_seconds`` es None, el TTL se resuelve por prefijo de clave.
        Degrada elegantemente (no-op) si no hay BD configurada.
        """
