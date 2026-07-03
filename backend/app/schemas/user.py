from typing import Optional

from pydantic import BaseModel, Field


class MiniProgramUserUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=32)
    language: Optional[str] = Field(default=None, max_length=16)
    explorer_level: Optional[int] = Field(default=None, ge=0, le=5)
    checkin_count: Optional[int] = Field(default=None, ge=0)
    contribution_count: Optional[int] = Field(default=None, ge=0)
    eco_credit: Optional[int] = Field(default=None, ge=0, le=100)
    is_member: Optional[bool] = None
    is_active: Optional[bool] = None


class MiniProgramUserOut(BaseModel):
    id: int
    openid: str
    nickname: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    language: str
    explorer_level: int
    checkin_count: int
    contribution_count: int
    eco_credit: int
    is_member: bool
    is_active: bool

    class Config:
        from_attributes = True


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
    note: Optional[str] = None
    review_note: Optional[str] = None
