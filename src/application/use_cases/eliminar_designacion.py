"""Caso de uso para eliminar físicamente una designación docente errónea."""

from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort


class EliminarDesignacionUseCase:
    """Orquesta la eliminación física de una designación docente."""

    def __init__(self, repository: DesignacionDocenteRepositoryPort) -> None:
        self._repository = repository

    def execute(self, id_designacion: str) -> bool:
        """Elimina la designación y sus bloques asociados."""
        return self._repository.eliminar(id_designacion.strip())
