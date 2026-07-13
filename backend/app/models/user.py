from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class MiniProgramUser(Base):
    __tablename__ = "mini_program_users"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(128), nullable=False, unique=True, index=True)
    nickname = Column(String(64), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    phone = Column(String(32), nullable=True)
    language = Column(String(16), default="zh-CN", nullable=False)
    explorer_level = Column(Integer, default=0, nullable=False)
    explore_points = Column(Integer, default=0, nullable=False)
    checkin_count = Column(Integer, default=0, nullable=False)
    contribution_count = Column(Integer, default=0, nullable=False)
    eco_credit = Column(Integer, default=100, nullable=False)
    is_member = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    can_upload_image = Column(Boolean, default=True, nullable=False)
    can_upload_video = Column(Boolean, default=True, nullable=False)
    can_comment = Column(Boolean, default=True, nullable=False)
    can_checkin = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PassLevelSetting(Base):
    __tablename__ = "pass_level_settings"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer, nullable=False, unique=True, index=True)
    name_zh = Column(String(64), nullable=False)
    name_en = Column(String(64), nullable=False)
    required_explore_points = Column(Integer, default=0, nullable=False)
    required_checkins = Column(Integer, default=0, nullable=False)
    required_contributions = Column(Integer, default=0, nullable=False)
    required_eco_credit = Column(Integer, default=0, nullable=False)
    requires_membership = Column(Boolean, default=False, nullable=False)
    unlock_benefit_zh = Column(String(512), nullable=False)
    unlock_benefit_en = Column(String(512), nullable=False)
    marker_color = Column(String(16), default="#2f6b4f", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MembershipPlan(Base):
    __tablename__ = "membership_plans"

    id = Column(Integer, primary_key=True, index=True)
    name_zh = Column(String(64), nullable=False)
    name_en = Column(String(64), nullable=False)
    duration_days = Column(Integer, default=30, nullable=False)
    price_cents = Column(Integer, default=0, nullable=False)
    required_explore_points = Column(Integer, default=0, nullable=False)
    benefits_zh = Column(String(512), nullable=False)
    benefits_en = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserMembership(Base):
    __tablename__ = "user_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=False, index=True)
    status = Column(String(32), default="active", nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("MiniProgramUser")
    plan = relationship("MembershipPlan")


class CheckinRecord(Base):
    __tablename__ = "checkin_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=False, index=True)
    status = Column(String(32), default="pending", nullable=False)
    latitude = Column(String(32), nullable=True)
    longitude = Column(String(32), nullable=True)
    image_url = Column(String(512), nullable=True)
    media_url = Column(String(512), nullable=True)
    media_type = Column(String(32), nullable=True)
    note = Column(String(512), nullable=True)
    review_note = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("MiniProgramUser")
    spot = relationship("ScenicSpot")
