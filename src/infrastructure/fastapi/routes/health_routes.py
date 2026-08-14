"""FastAPI routing for health check."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.adapters.controllers.dependencies import get_health_controller
from src.adapters.controllers.health_controller import HealthController
from src.application.dtos.common_dto import HealthDTO

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthDTO,
    summary="Health check endpoint",
    description="Check operational availability and version.",
)
async def health_check(
    controller: Annotated[HealthController, Depends(get_health_controller)],
) -> HealthDTO:
    """Return health status."""
    return controller.get_health()
