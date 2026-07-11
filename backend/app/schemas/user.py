from typing import Optional

from pydantic import BaseModel, Field


class MiniProgramUserUpdate(BaseModel):
    openid: Optional[str] = Field(default=None, max_length=128)
    nickname: Optional[str] = Field(default=None, max_length=64)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    phone: Optional[str] = Field(default=None, max_length=32)
    language: Optional[str] = Field(default=None, max_length=16)
    explorer_level: Optional[int] = Field(default=None, ge=0, le=5)
    explore_points: Optional[int] = Field(default=None, ge=0)
    checkin_count: Optional[int] = Field(default=None, ge=0)
    contribution_count: Optional[int] = Field(default=None, ge=0)
    eco_credit: Optional[int] = Field(default=None, ge=0, le=100)
    is_member: Optional[bool] = None
    is_active: Optional[bool] = None
    can_upload_image: Optional[bool] = None
    can_upload_video: Optional[bool] = None
    can_comment: Optional[bool] = None
    can_checkin: Optional[bool] = None


class MiniProgramUserCreate(BaseModel):
    openid: str = Field(..., max_length=128)
    nickname: str = Field(..., max_length=64)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    phone: Optional[str] = Field(default=None, max_length=32)
    language: str = Field(default="zh-CN", max_length=16)
    explorer_level: int = Field(default=0, ge=0, le=5)
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


class MiniProgramUserOut(BaseModel):
    id: int
    openid: str
    nickname: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    language: str
    explorer_level: int
    explore_points: int
    checkin_count: int
    contribution_count: int
    eco_credit: int
    is_member: bool
    is_active: bool
    can_upload_image: bool
    can_upload_video: bool
    can_comment: bool
    can_checkin: bool

    class Config:
        from_attributes = True


class MiniProgramLoginIn(BaseModel):
    code: str = Field(..., max_length=128)
    nickname: Optional[str] = Field(default=None, max_length=64)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    language: str = Field(default="zh-CN", max_length=16)


class PassLevelSettingUpdate(BaseModel):
    name_zh: Optional[str] = Field(default=None, max_length=64)
    name_en: Optional[str] = Field(default=None, max_length=64)
    required_checkins: Optional[int] = Field(default=None, ge=0)
    required_contributions: Optional[int] = Field(default=None, ge=0)
    required_eco_credit: Optional[int] = Field(default=None, ge=0, le=100)
    requires_membership: Optional[bool] = None
    unlock_benefit_zh: Optional[str] = Field(default=None, max_length=512)
    unlock_benefit_en: Optional[str] = Field(default=None, max_length=512)
    is_active: Optional[bool] = None


class PassLevelSettingOut(BaseModel):
    id: int
    level: int
    name_zh: str
    name_en: str
    required_checkins: int
    required_contributions: int
    required_eco_credit: int
    requires_membership: bool
    unlock_benefit_zh: str
    unlock_benefit_en: str
    is_active: bool

    class Config:
        from_attributes = True


class MembershipPlanUpdate(BaseModel):
    name_zh: Optional[str] = Field(default=None, max_length=64)
    name_en: Optional[str] = Field(default=None, max_length=64)
    duration_days: Optional[int] = Field(default=None, ge=1)
    price_cents: Optional[int] = Field(default=None, ge=0)
    benefits_zh: Optional[str] = Field(default=None, max_length=512)
    benefits_en: Optional[str] = Field(default=None, max_length=512)
    is_active: Optional[bool] = None


class MembershipPlanOut(BaseModel):
    id: int
    name_zh: str
    name_en: str
    duration_days: int
    price_cents: int
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
    media_url: Optional[str] = Field(default=None, max_length=512)
    media_type: Optional[str] = Field(default=None, max_length=32)
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
