"""Presenter for formatting salary simulation output responses."""

from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.simulation_dto import SimulacionSueldoResponseDTO


class SimulationPresenter:
    """Formats Simulation DTOs into standardized API envelopes."""

    @staticmethod
    def present(
        dto: SimulacionSueldoResponseDTO,
    ) -> APIResponseDTO[SimulacionSueldoResponseDTO]:
        """Wrap simulation DTO into API response envelope."""
        return APIResponseDTO(
            success=True,
            data=dto,
        )
