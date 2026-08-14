"""Domain ports for salary settlement and paritary data access."""

from abc import ABC, abstractmethod

from src.domain.liquidacion.value_objects import ParametrosParitaria


class ParitariaRepositoryPort(ABC):
    """Port interface for loading teacher paritary rates by period."""

    @abstractmethod
    def obtener_por_periodo(self, periodo: str) -> ParametrosParitaria:
        """Fetch paritary parameters for given YYYYMM period."""
