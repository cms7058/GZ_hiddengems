from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MiniProgramUserUpdate(BaseModel):
    openid: Optional[str] = Field(default=None, max_length=128)
    nickname: Optional[str] = Field(default=None, max_length=64)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    phone: Optional[str] = Field(default=None, max_length=32)
    safety_level: Optional[str] = Field(default=None, pattern="^(general|risk|quality)$")
    language: Optional[str] = Field(default=None, max_length=16)
    explore_points: Optional[int] = Field(default=None, ge=0)
    checkin_count: Optional[int] = Field(default=None, ge=0)
    is_member: Optional[bool] = None
    is_active: Optional[bool] = None
    can_upload_image: Optional[bool] = None
    can_upload_video: Optional[bool] = None
    can_comment: Optional[bool] = None
    can_checkin: Optional[bool] = None
    can_recommend_spot: Optional[bool] = None
    can_like_comment: Optional[bool] = None
    can_share: Optional[bool] = None


class MiniProgramUserCreate(BaseModel):
    openid: str = Field(..., max_length=128)
    nickname: str = Field(..., max_length=64)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    phone: Optional[str] = Field(default=None, max_length=32)
    safety_level: str = Field(default="general", pattern="^(general|risk|quality)$")
    language: str = Field(default="zh-CN", max_length=16)
    explore_points: int = Field(default=0, ge=0)
    checkin_count: int = Field(default=0, ge=0)
    contribution_count: int = Field(default=0, ge=0)
    eco_credit: int = Field(default=100, ge=0, le=100)
    is_member: bool = False
    is_active: bool = True
    can_upload_image: bool = True
    can_upload_video: bool = True
    can_comment: bool = True
    can_checkin: bool = True
    can_recommend_spot: bool = True
    can_like_comment: bool = True
    can_share: bool = True


class MiniProgramUserOut(BaseModel):
    id: int
    openid: str
    nickname: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    phone_verified_at: Optional[datetime] = None
    language: str
    explore_points: int
    checkin_count: int
    contribution_count: int
    eco_credit: int
    share_count: int = 0
    referral_registered_count: int = 0
    approved_recommendation_count: int = 0
    like_received_count: int = 0
    like_given_count: int = 0
    safety_level: str = "general"
    is_member: bool
    is_active: bool
    can_upload_image: bool
    can_upload_video: bool
    can_comment: bool
    can_checkin: bool
    can_recommend_spot: bool = True
    can_like_comment: bool = True
    can_share: bool = True
    checkin_warning_count: int = 0
    checkin_suspicious_count: int = 0
    checkin_watch_count: int = 0
    checkin_risk_status: str = "normal"
    checkin_risk_level: str = "normal"
    checkin_permission_disabled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MiniProgramLoginIn(BaseModel):
    code: str = Field(..., max_length=128)
    nickname: Optional[str] = Field(default=None, max_length=64)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    language: str = Field(default="zh-CN", max_length=16)
    referrer_token: Optional[str] = Field(default=None, max_length=64)


class PassLevelSettingCreate(BaseModel):
    level: int = Field(..., ge=0, le=99)
    name_zh: str = Field(..., max_length=64)
    name_en: str = Field(..., max_length=64)
    required_explore_points: int = Field(default=0, ge=0)
    checkin_points: int = Field(default=0, ge=0)
    requires_membership: bool = False
    unlock_benefit_zh: str = Field(..., max_length=512)
    unlock_benefit_en: str = Field(..., max_length=512)
    unlock_rule_zh: str = Field(default="", max_length=1024)
    unlock_rule_en: str = Field(default="", max_length=1024)
    marker_color: str = Field(default="#2f6b4f", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: bool = True


class PassLevelSettingUpdate(BaseModel):
    level: Optional[int] = Field(default=None, ge=0, le=99)
    name_zh: Optional[str] = Field(default=None, max_length=64)
    name_en: Optional[str] = Field(default=None, max_length=64)
    required_explore_points: Optional[int] = Field(default=None, ge=0)
    checkin_points: Optional[int] = Field(default=None, ge=0)
    requires_membership: Optional[bool] = None
    unlock_benefit_zh: Optional[str] = Field(default=None, max_length=512)
    unlock_benefit_en: Optional[str] = Field(default=None, max_length=512)
    unlock_rule_zh: Optional[str] = Field(default=None, max_length=1024)
    unlock_rule_en: Optional[str] = Field(default=None, max_length=1024)
    marker_color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None


class PassLevelSettingOut(BaseModel):
    id: int
    level: int
    name_zh: str
    name_en: str
    required_explore_points: int
    checkin_points: int
    requires_membership: bool
    unlock_benefit_zh: str
    unlock_benefit_en: str
    unlock_rule_zh: str = ""
    unlock_rule_en: str = ""
    marker_color: str
    is_active: bool

    class Config:
        from_attributes = True


class MembershipPlanUpdate(BaseModel):
    name_zh: Optional[str] = Field(default=None, max_length=64)
    name_en: Optional[str] = Field(default=None, max_length=64)
    duration_days: Optional[int] = Field(default=None, ge=1)
    price_cents: Optional[int] = Field(default=None, ge=0)
    required_explore_points: Optional[int] = Field(default=None, ge=0)
    benefits_zh: Optional[str] = Field(default=None, max_length=512)
    benefits_en: Optional[str] = Field(default=None, max_length=512)
    is_active: Optional[bool] = None



class MembershipPlanCreate(BaseModel):
    name_zh: str = Field(..., max_length=64)
    name_en: str = Field(..., max_length=64)
    duration_days: int = Field(default=30, ge=1)
    price_cents: int = Field(default=0, ge=0)
    required_explore_points: int = Field(default=0, ge=0)
    benefits_zh: str = Field(..., max_length=512)
    benefits_en: str = Field(..., max_length=512)
    is_active: bool = True


class MembershipPlanOut(BaseModel):
    id: int
    name_zh: str
    name_en: str
    duration_days: int
    price_cents: int
    required_explore_points: int
    benefits_zh: str
    benefits_en: str
    is_active: bool

    class Config:
        from_attributes = True


class UserMembershipOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    plan_id: int
    plan_name_zh: str
    status: str
    started_at: Optional[str] = None
    expires_at: Optional[str] = None


class CheckinReviewUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|approved|rejected)$")
    review_note: Optional[str] = Field(default=None, max_length=512)


class CheckinCreate(BaseModel):
    user_id: int
    spot_id: int
    latitude: Optional[str] = Field(default=None, max_length=32)
    longitude: Optional[str] = Field(default=None, max_length=32)
    image_url: Optional[str] = Field(default=None, max_length=512)
    note: Optional[str] = Field(default=None, max_length=512)


class CheckinRecordOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    spot_id: int
    spot_name_zh: str
    status: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    image_url: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    note: Optional[str] = None
    review_note: Optional[str] = None
    awarded_explore_points: int = 0
    promoted_spot_image_id: Optional[int] = None
    checkin_distance_meters: Optional[int] = None
    route_distance_meters: Optional[int] = None
    route_duration_seconds: Optional[int] = None
    elapsed_seconds: Optional[int] = None
    travel_time_ratio: Optional[float] = None
    risk_status: str = "normal"
    risk_reason: Optional[str] = None
    previous_checkin_id: Optional[int] = None
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
