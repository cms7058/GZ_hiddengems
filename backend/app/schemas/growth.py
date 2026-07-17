from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SafetyLevelPolicyUpdate(BaseModel):
    name_zh: Optional[str] = Field(default=None, max_length=32)
    name_en: Optional[str] = Field(default=None, max_length=32)
    can_upload_image: Optional[bool] = None
    can_upload_video: Optional[bool] = None
    can_comment: Optional[bool] = None
    can_checkin: Optional[bool] = None
    can_recommend_spot: Optional[bool] = None
    can_like_comment: Optional[bool] = None
    can_share: Optional[bool] = None
    is_active: Optional[bool] = None


class SafetyLevelPolicyOut(SafetyLevelPolicyUpdate):
    id: int
    level: str

    class Config:
        from_attributes = True


class PointRuleUpdate(BaseModel):
    name_zh: Optional[str] = Field(default=None, max_length=64)
    name_en: Optional[str] = Field(default=None, max_length=64)
    points: Optional[int] = Field(default=None, ge=0)
    is_enabled: Optional[bool] = None
    daily_limit: Optional[int] = Field(default=None, ge=0)
    total_limit: Optional[int] = Field(default=None, ge=0)


class PointRuleOut(PointRuleUpdate):
    id: int
    code: str

    class Config:
        from_attributes = True


class PointLedgerOut(BaseModel):
    id: int
    user_id: int
    rule_code: str
    reference_type: str
    reference_id: int
    points: int
    status: str
    note: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SpotRecommendationCreate(BaseModel):
    user_id: int
    name_zh: str = Field(..., max_length=128)
    name_en: str = Field(default="", max_length=128)
    summary_zh: str = Field(..., max_length=512)
    summary_en: str = Field(default="", max_length=512)
    description_zh: Optional[str] = None
    description_en: Optional[str] = None
    city: str = Field(..., max_length=64)
    county: str = Field(..., max_length=64)
    latitude: Optional[str] = Field(default=None, max_length=32)
    longitude: Optional[str] = Field(default=None, max_length=32)
    river_name: Optional[str] = Field(default=None, max_length=128)
    river_upstream_latitude: Optional[str] = Field(default=None, max_length=32)
    river_upstream_longitude: Optional[str] = Field(default=None, max_length=32)
    recommendation_level: int = Field(default=0, ge=0, le=99)
    tag_ids: list[int] = Field(default_factory=list)
    media: list[dict] = Field(default_factory=list)


class SpotRecommendationOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    name_zh: str
    name_en: str
    summary_zh: str
    summary_en: str
    description_zh: Optional[str] = None
    description_en: Optional[str] = None
    city: str
    county: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    river_name: Optional[str] = None
    river_upstream_latitude: Optional[str] = None
    river_upstream_longitude: Optional[str] = None
    recommendation_level: int
    tag_ids: list[int] = Field(default_factory=list)
    status: str
    review_note: Optional[str] = None
    approved_spot_id: Optional[int] = None
    media: list[dict] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None


class SpotRecommendationReview(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    review_note: Optional[str] = Field(default=None, max_length=512)
