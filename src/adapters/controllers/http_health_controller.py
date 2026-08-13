"""HTTP controller for health check endpoint."""

from fastapi import APIRouter

from src.application.dtos.common_dto import HealthDTO

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthDTO,
    summary="Health check endpoint",
    description="Check operational availability and version.",
)
async def health_check() -> HealthDTO:
    return HealthDTO(
        status="ok",
        version="0.1.0",
        service="datamaq-hub",
    )
