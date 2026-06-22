from pydantic import BaseModel, Field

from app.schemas.common import SuccessResponse


class LoginRequest(BaseModel):
    """Request body for user login."""

    username: str = Field(
        description="UIT username (student ID)",
        examples=["24520378"],
    )
    password: str = Field(
        description="UIT password",
        examples=["password123"],
    )


class LoginResponse(SuccessResponse):
    """Response returned after successful login."""

    token: str = Field(
        description="Session token to be used in Authorization header",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class LogoutResponse(SuccessResponse):
    """Response returned after logout."""

    pass