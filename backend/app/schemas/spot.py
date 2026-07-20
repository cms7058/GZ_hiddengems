from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.schemas.content import SpotImageOut

from app.schemas.content import RecommendationOut, TravelNoteOut, UserCommentOut
from app.schemas.user import CheckinRecordOut


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


class WechatChannelVideoBase(BaseModel):
    media_type: Literal["wechat_channel"] = "wechat_channel"
    finder_user_name: str = Field(..., min_length=1, max_length=128)
    feed_id: str = Field(..., min_length=1, max_length=256)
    title: str = Field(..., min_length=1, max_length=256)
    cover_url: str = Field(..., min_length=1, max_length=512)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("cover_url")
    @classmethod
    def validate_cover_url(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Wechat channel cover URL must be a valid HTTP(S) URL")
        return normalized


class WechatChannelVideoOut(WechatChannelVideoBase):
    id: int
    spot_id: int
    display_url: Optional[str] = None


class SpotCreate(BaseModel):
    name_zh: str = Field(..., max_length=128)
    name_en: str = Field(..., max_length=128)
    locked_name_zh: Optional[str] = Field(default=None, max_length=128)
    locked_name_en: Optional[str] = Field(default=None, max_length=128)
    summary_zh: str = Field(..., max_length=512)
    summary_en: str = Field(..., max_length=512)
    description_zh: Optional[str] = None
    description_en: Optional[str] = None
    city: str = Field(..., max_length=64)
    county: str = Field(..., max_length=64)
    latitude: float
    longitude: float
    coordinate_system: Literal["gcj02", "wgs84", "bd09"] = "gcj02"
    river_name: Optional[str] = Field(default=None, max_length=128)
    river_upstream_latitude: Optional[float] = None
    river_upstream_longitude: Optional[float] = None
    video_channel_urls: list[str] = Field(default_factory=list, max_length=10)
    wechat_channel_videos: list[WechatChannelVideoBase] = Field(default_factory=list, max_length=100)
    visibility_level: str = "public"
    review_status: str = "draft"
    recommendation_level: int = Field(..., ge=0, le=99)
    required_explore_points: int = Field(default=0, ge=0)
    checkin_radius_meters: int = 300
    is_active: bool = True
    tag_ids: list[int] = Field(default_factory=list)

    @field_validator("video_channel_urls")
    @classmethod
    def validate_video_channel_urls(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            url = value.strip()
            parsed = urlparse(url)
            if len(url) > 512 or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Video channel URLs must be valid HTTP(S) URLs")
            if url not in normalized:
                normalized.append(url)
        return normalized


class SpotUpdate(BaseModel):
    name_zh: Optional[str] = Field(default=None, max_length=128)
    name_en: Optional[str] = Field(default=None, max_length=128)
    locked_name_zh: Optional[str] = Field(default=None, max_length=128)
    locked_name_en: Optional[str] = Field(default=None, max_length=128)
    summary_zh: Optional[str] = Field(default=None, max_length=512)
    summary_en: Optional[str] = Field(default=None, max_length=512)
    description_zh: Optional[str] = None
    description_en: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=64)
    county: Optional[str] = Field(default=None, max_length=64)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coordinate_system: Optional[Literal["gcj02", "wgs84", "bd09"]] = None
    river_name: Optional[str] = Field(default=None, max_length=128)
    river_upstream_latitude: Optional[float] = None
    river_upstream_longitude: Optional[float] = None
    video_channel_urls: Optional[list[str]] = Field(default=None, max_length=10)
    wechat_channel_videos: Optional[list[WechatChannelVideoBase]] = Field(default=None, max_length=100)
    visibility_level: Optional[str] = None
    review_status: Optional[str] = None
    recommendation_level: Optional[int] = Field(default=None, ge=0, le=99)
    required_explore_points: Optional[int] = Field(default=None, ge=0)
    checkin_radius_meters: Optional[int] = None
    is_active: Optional[bool] = None
    tag_ids: Optional[list[int]] = None

    @field_validator("video_channel_urls")
    @classmethod
    def validate_video_channel_urls(cls, values: Optional[list[str]]) -> Optional[list[str]]:
        if values is None:
            return values
        return SpotCreate.validate_video_channel_urls(values)


class ReviewStatusUpdate(BaseModel):
    review_status: str = Field(..., pattern="^(draft|pending|approved|rejected)$")


class SpotChildPointBase(BaseModel):
    name: str = Field(..., max_length=128)
    latitude: float
    longitude: float
    coordinate_system: Literal["gcj02", "wgs84", "bd09"] = "gcj02"
    note: Optional[str] = Field(default=None, max_length=512)
    fetch_weather: bool = False
    sort_order: int = 0
    is_active: bool = True


class SpotChildPointCreate(SpotChildPointBase):
    pass


class SpotChildPointUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coordinate_system: Optional[Literal["gcj02", "wgs84", "bd09"]] = None
    note: Optional[str] = Field(default=None, max_length=512)
    fetch_weather: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class SpotChildPointOut(SpotChildPointBase):
    id: int
    spot_id: int

    class Config:
        from_attributes = True


class SpotAdminOut(SpotCreate):
    id: int
    spot_code: Optional[str] = None
    cover_image_url: Optional[str] = None
    wechat_channel_videos: list[WechatChannelVideoOut] = Field(default_factory=list)
    tags: list[LocalizedTag] = Field(default_factory=list)
    child_points: list[SpotChildPointOut] = Field(default_factory=list)

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
    required_explore_points: int
    user_explore_points: int = 0
    is_unlocked: bool
    is_precise_location: bool
    recommendation_level: int
    marker_color: str = "#2f6b4f"
    cover_image_url: Optional[str] = None
    tags: list[LocalizedTag]


class LockedSpotPreviewOut(BaseModel):
    """Nearby locked spot data without coordinates or navigation metadata."""

    id: int
    name: str
    summary: str
    city: str
    county: str
    required_explore_points: int
    user_explore_points: int
    recommendation_level: int
    marker_color: str = "#2f6b4f"
    distance_km: float
    tags: list[LocalizedTag] = Field(default_factory=list)
    images: list[SpotImageOut] = Field(default_factory=list)


class LockedNearbySpotCountOut(BaseModel):
    count: int


class HomeSpotOut(BaseModel):
    """Home filter chip data. Locked spots deliberately omit location fields."""

    id: int
    name: str
    locked_name: str = ""
    recommendation_level: int
    marker_color: str = "#2f6b4f"
    is_unlocked: bool
    required_explore_points: int
    user_explore_points: int
    tags: list[LocalizedTag] = Field(default_factory=list)


class LockedSpotDetailOut(BaseModel):
    """Locked spot detail intentionally omits all location metadata."""

    id: int
    name: str
    summary: str
    description: Optional[str] = None
    required_explore_points: int
    user_explore_points: int
    recommendation_level: int
    marker_color: str = "#2f6b4f"
    tags: list[LocalizedTag] = Field(default_factory=list)
    images: list[SpotImageOut] = Field(default_factory=list)


class SpotDetailOut(MapSpotOut):
    description: Optional[str] = None
    checkin_radius_meters: int
    video_channel_urls: list[str] = Field(default_factory=list)
    wechat_channel_videos: list[WechatChannelVideoOut] = Field(default_factory=list)
    images: list[SpotImageOut] = Field(default_factory=list)
    travel_notes: list[TravelNoteOut] = Field(default_factory=list)
    comments: list[UserCommentOut] = Field(default_factory=list)
    my_checkins: list[CheckinRecordOut] = Field(default_factory=list)
    lifestyle_recommendations: list[RecommendationOut] = Field(default_factory=list)
