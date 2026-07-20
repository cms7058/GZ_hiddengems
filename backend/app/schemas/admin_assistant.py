from typing import Literal

from pydantic import BaseModel, Field


class AdminAssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    mode: Literal["guide", "spot_summary", "coordinate", "review", "archive"] = "guide"


class ContentReviewRequest(BaseModel):
    content_type: Literal["travel_note", "comment"]
    content_id: int
