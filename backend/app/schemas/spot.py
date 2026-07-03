from typing import Optional

from pydantic import BaseModel, Field


class LocalizedTag(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None


class TagCreate(BaseModel):
    name_zh: str = Field(..., max_length=64)
    name_en: str = Field(..., max_length=64)
    icon: Optional[str] = Field(default=None, max_length=64)
    sort_order: int = 0
    is_active: bool = True


class TagUpdate(BaseModel):
    name_zh: Optional[str] = Field(default=None, max_length=64)
    name_en: Optional[str] = Field(default=None, max_length=64)
    icon: Optional[str] = Field(default=None, max_length=64)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class TagAdminOut(TagCreate):
    id: int

    class Config:
        from_attributes = True


class SpotCreate(BaseModel):
    name_zh: str = Field(..., max_length=128)
    name_en: str = Field(..., max_length=128)
    summary_zh: str = Field(..., max_length=512)
    summary_en: str = Field(..., max_length=512)
    description_zh: Optional[str] = None
    description_en: Optional[str] = None
    city: str = Field(..., max_length=64)
    county: str = Field(..., max_length=64)
    latitude: float
    longitude: float
    visibility_level: str = "public"
    review_status: str = "draft"
    recommendation_level: int = 1
    checkin_radius_meters: int = 300
    is_active: bool = True
    tag_ids: list[int] = Field(default_factory=list)


class SpotUpdate(BaseModel):
    name_zh: Optional[str] = Field(default=None, max_length=128)
    name_en: Optional[str] = Field(default=None, max_length=128)
    summary_zh: Optional[str] = Field(default=None, max_length=512)
    summary_en: Optional[str] = Field(default=None, max_length=512)
    description_zh: Optional[str] = None
    description_en: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=64)
    county: Optional[str] = Field(default=None, max_length=64)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    visibility_level: Optional[str] = None
    review_status: Optional[str] = None
    recommendation_level: Optional[int] = None
    checkin_radius_meters: Optional[int] = None
    is_active: Optional[bool] = None
    tag_ids: Optional[list[int]] = None


class ReviewStatusUpdate(BaseModel):
    review_status: str = Field(..., pattern="^(draft|pending|approved|rejected)$")


class SpotAdminOut(SpotCreate):
    id: int
    tags: list[LocalizedTag] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MapSpotOut(BaseModel):
    id: int
    name: str
    summary: str
    city: str
    county: str
    latitude: float
    longitude: float
    visibility_level: str
    is_precise_location: bool
    recommendation_level: int
    tags: list[LocalizedTag]


class SpotDetailOut(MapSpotOut):
    description: Optional[str] = None
    checkin_radius_meters: int
