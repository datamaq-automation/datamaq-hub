"""Common Pydantic schemas for Datamaq Hub."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Health check response schema."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok", description="Health status")
    version: str = Field(default="0.1.0", description="API version")
    service: str = Field(default="datamaq-hub", description="Service name")


class ErrorDetail(BaseModel):
    """Detailed error schema."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Internal error code")
    message: str = Field(description="User-friendly error message")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional context or validation details"
    )


class ErrorResponse(BaseModel):
    """Standardized error envelope."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(default=False, description="Operation success indicator")
    error: ErrorDetail = Field(description="Error information")


class APIResponse(BaseModel, Generic[T]):
    """Standardized generic API response envelope."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(default=True, description="Operation success indicator")
    data: T = Field(description="Payload data")
