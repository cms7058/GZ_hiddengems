from typing import Optional

from pydantic import BaseModel, Field


class SpotImageOut(BaseModel):
    id: int
    spot_id: int
    image_url: str
    caption: Optional[str] = None
    sort_order: int
    is_cover: bool
    is_active: bool

    class Config:
        from_attributes = True


class SpotImageUpdate(BaseModel):
    caption: Optional[str] = Field(default=None, max_length=256)
    sort_order: Optional[int] = None
    is_cover: Optional[bool] = None
    is_active: Optional[bool] = None


class ContentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|approved|rejected|hidden)$")
    is_featured: Optional[bool] = None


class TravelNoteOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    spot_id: Optional[int] = None
    spot_name_zh: Optional[str] = None
    title: str
    content: str
    status: str
    is_featured: bool


class UserCommentOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    spot_id: Optional[int] = None
    spot_name_zh: Optional[str] = None
    content: str
    status: str


class RecommendationCreate(BaseModel):
    category: str = Field(..., pattern="^(clothing|food|hotel|transport)$")
    name_zh: str = Field(..., max_length=128)
    name_en: str = Field(..., max_length=128)
    summary_zh: str = Field(..., max_length=512)
    summary_en: str = Field(..., max_length=512)
    city: str = Field(..., max_length=64)
    county: str = Field(..., max_length=64)
    address: Optional[str] = Field(default=None, max_length=256)
    contact: Optional[str] = Field(default=None, max_length=128)
    price_level: str = Field(default="mid", max_length=32)
    recommendation_level: int = Field(default=1, ge=1, le=5)
    is_active: bool = True


class RecommendationUpdate(BaseModel):
    category: Optional[str] = Field(default=None, pattern="^(clothing|food|hotel|transport)$")
    name_zh: Optional[str] = Field(default=None, max_length=128)
    name_en: Optional[str] = Field(default=None, max_length=128)
    summary_zh: Optional[str] = Field(default=None, max_length=512)
    summary_en: Optional[str] = Field(default=None, max_length=512)
    city: Optional[str] = Field(default=None, max_length=64)
    county: Optional[str] = Field(default=None, max_length=64)
    address: Optional[str] = Field(default=None, max_length=256)
    contact: Optional[str] = Field(default=None, max_length=128)
    price_level: Optional[str] = Field(default=None, max_length=32)
    recommendation_level: Optional[int] = Field(default=None, ge=1, le=5)
    is_active: Optional[bool] = None


class RecommendationOut(RecommendationCreate):
    id: int

    class Config:
        from_attributes = True
