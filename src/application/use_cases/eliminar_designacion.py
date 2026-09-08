from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.recibos.ports import SeguimientoNoLiquidadosRepositoryPort


class EliminarDesignacionUseCase:
    """Orquesta la eliminación física de una designación docente."""

    def __init__(
        self,
        repository: DesignacionDocenteRepositoryPort,
        seguimiento_repository: SeguimientoNoLiquidadosRepositoryPort | None = None,
    ) -> None:
        self._repository = repository
        self._seguimiento_repository = seguimiento_repository

    def execute(self, id_designacion: str) -> bool:
        """Elimina la designación y sus bloques asociados, limpiando los registros de seguimiento asociados."""
        clean_id = id_designacion.strip()
        eliminado = self._repository.eliminar(clean_id)
        if eliminado and self._seguimiento_repository:
            self._seguimiento_repository.eliminar_por_designacion(clean_id)
        return eliminado
