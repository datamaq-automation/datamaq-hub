"""Pure transport-agnostic controller for health check."""

from src.application.dtos.common_dto import HealthDTO


class HealthController:
    """Handles health status checks independently of HTTP framework."""

    def get_health(self) -> HealthDTO:
        """Return application health information."""
        return HealthDTO(
            status="ok",
            version="0.1.0",
            service="datamaq-hub",
        )
