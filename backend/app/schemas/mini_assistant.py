from typing import Optional

from pydantic import BaseModel, Field, model_validator


class MiniAssistantQuery(BaseModel):
    """A database-backed question from the mini-program assistant."""

    user_id: int = Field(..., ge=1)
    query: str = Field(..., min_length=1, max_length=500)
    lang: str = Field(default="zh-CN", max_length=16)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def require_coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self
