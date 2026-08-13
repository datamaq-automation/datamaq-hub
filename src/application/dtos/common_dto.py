"""Common application response and error DTOs."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class HealthDTO(BaseModel):
    """Health status DTO."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok", description="Status string")
    version: str = Field(default="0.1.0", description="Application version")
    service: str = Field(default="datamaq-hub", description="Service name")


class ErrorDetailDTO(BaseModel):
    """Error detail information DTO."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Internal error code")
    message: str = Field(description="Human readable message")
    details: dict[str, Any] | None = Field(default=None, description="Detailed context")


class ErrorResponseDTO(BaseModel):
    """Error envelope DTO."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(default=False, description="Success indicator")
    error: ErrorDetailDTO = Field(description="Error information")


class APIResponseDTO(BaseModel, Generic[T]):
    """Standard generic API response envelope."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(default=True, description="Success indicator")
    data: T = Field(description="Response data")
