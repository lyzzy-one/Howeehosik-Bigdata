"""Request models."""
from pydantic import BaseModel, Field


class SafetyScoreRequest(BaseModel):
    """Request model for safety score calculation."""

    address: str = Field(
        ...,
        description="서울시 내 주소",
        examples=["서울특별시 관악구 신림동 123-45"]
    )
