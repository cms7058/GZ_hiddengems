from typing import Optional

from pydantic import BaseModel, Field


class SpotImageOut(BaseModel):
    id: int
    spot_id: int
    image_url: str
    display_url: Optional[str] = None
    media_type: str = "image"
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


class TravelNoteCreate(BaseModel):
    user_id: int
    spot_id: int
    title: str = Field(..., max_length=128)
    content: str
    image_url: Optional[str] = Field(default=None, max_length=512)
    status: str = Field(default="pending", pattern="^(pending|approved|rejected|hidden)$")
    is_featured: bool = False


class TravelNoteUpdate(BaseModel):
    user_id: Optional[int] = None
    spot_id: Optional[int] = None
    title: Optional[str] = Field(default=None, max_length=128)
    content: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=512)
    status: Optional[str] = Field(default=None, pattern="^(pending|approved|rejected|hidden)$")
    is_featured: Optional[bool] = None


class TravelNoteOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    avatar_url: Optional[str] = None
    spot_id: Optional[int] = None
    spot_name_zh: Optional[str] = None
    title: str
    content: str
    image_url: Optional[str] = None
    display_url: Optional[str] = None
    status: str
    is_featured: bool


class UserCommentCreate(BaseModel):
    user_id: int
    spot_id: int
    content: str = Field(..., max_length=512)
    image_url: Optional[str] = Field(default=None, max_length=512)
    status: str = Field(default="pending", pattern="^(pending|approved|rejected|hidden)$")


class UserCommentUpdate(BaseModel):
    user_id: Optional[int] = None
    spot_id: Optional[int] = None
    content: Optional[str] = Field(default=None, max_length=512)
    image_url: Optional[str] = Field(default=None, max_length=512)
    status: Optional[str] = Field(default=None, pattern="^(pending|approved|rejected|hidden)$")


class UserCommentOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    avatar_url: Optional[str] = None
    spot_id: Optional[int] = None
    spot_name_zh: Optional[str] = None
    content: str
    image_url: Optional[str] = None
    display_url: Optional[str] = None
    status: str


class RecommendationCreate(BaseModel):
    spot_id: int
    category: str = Field(..., pattern="^(clothing|food|hotel|transport)$")
    name_zh: str = Field(..., max_length=128)
    name_en: str = Field(..., max_length=128)
    summary_zh: str = Field(..., max_length=512)
    summary_en: str = Field(..., max_length=512)
    city: str = Field(..., max_length=64)
    county: str = Field(..., max_length=64)
    address: Optional[str] = Field(default=None, max_length=256)
    contact: Optional[str] = Field(default=None, max_length=128)
    image_url: Optional[str] = Field(default=None, max_length=512)
    price_level: str = Field(default="mid", max_length=32)
    recommendation_level: int = Field(default=1, ge=1, le=99)
    is_active: bool = True


class RecommendationUpdate(BaseModel):
    spot_id: Optional[int] = None
    category: Optional[str] = Field(default=None, pattern="^(clothing|food|hotel|transport)$")
    name_zh: Optional[str] = Field(default=None, max_length=128)
    name_en: Optional[str] = Field(default=None, max_length=128)
    summary_zh: Optional[str] = Field(default=None, max_length=512)
    summary_en: Optional[str] = Field(default=None, max_length=512)
    city: Optional[str] = Field(default=None, max_length=64)
    county: Optional[str] = Field(default=None, max_length=64)
    address: Optional[str] = Field(default=None, max_length=256)
    contact: Optional[str] = Field(default=None, max_length=128)
    image_url: Optional[str] = Field(default=None, max_length=512)
    price_level: Optional[str] = Field(default=None, max_length=32)
    recommendation_level: Optional[int] = Field(default=None, ge=1, le=99)
    is_active: Optional[bool] = None


class RecommendationOut(RecommendationCreate):
    id: int
    spot_name_zh: Optional[str] = None
    image_url: Optional[str] = None
    display_url: Optional[str] = None

    class Config:
        from_attributes = True
