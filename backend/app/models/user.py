from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class MiniProgramUser(Base):
    __tablename__ = "mini_program_users"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(128), nullable=False, unique=True, index=True)
    nickname = Column(String(64), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    phone = Column(String(32), nullable=True)
    phone_verified_at = Column(DateTime(timezone=True), nullable=True)
    language = Column(String(16), default="zh-CN", nullable=False)
    explore_points = Column(Integer, default=0, nullable=False)
    checkin_count = Column(Integer, default=0, nullable=False)
    contribution_count = Column(Integer, default=0, nullable=False)
    eco_credit = Column(Integer, default=100, nullable=False)
    share_count = Column(Integer, default=0, nullable=False)
    referral_registered_count = Column(Integer, default=0, nullable=False)
    approved_recommendation_count = Column(Integer, default=0, nullable=False)
    like_received_count = Column(Integer, default=0, nullable=False)
    like_given_count = Column(Integer, default=0, nullable=False)
    invited_by_user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=True, index=True)
    safety_level = Column(String(16), default="general", nullable=False)
    last_checkin_at = Column(DateTime(timezone=True), nullable=True)
    is_member = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    can_upload_image = Column(Boolean, default=True, nullable=False)
    can_upload_video = Column(Boolean, default=True, nullable=False)
    can_comment = Column(Boolean, default=True, nullable=False)
    can_checkin = Column(Boolean, default=True, nullable=False)
    can_recommend_spot = Column(Boolean, default=True, nullable=False)
    can_like_comment = Column(Boolean, default=True, nullable=False)
    can_share = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserSafetyLevelPolicy(Base):
    __tablename__ = "user_safety_level_policies"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(16), nullable=False, unique=True, index=True)
    name_zh = Column(String(32), nullable=False)
    name_en = Column(String(32), nullable=False)
    can_upload_image = Column(Boolean, default=True, nullable=False)
    can_upload_video = Column(Boolean, default=True, nullable=False)
    can_comment = Column(Boolean, default=True, nullable=False)
    can_checkin = Column(Boolean, default=True, nullable=False)
    can_recommend_spot = Column(Boolean, default=True, nullable=False)
    can_like_comment = Column(Boolean, default=True, nullable=False)
    can_share = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PointRule(Base):
    __tablename__ = "point_rules"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name_zh = Column(String(64), nullable=False)
    name_en = Column(String(64), nullable=False)
    points = Column(Integer, default=0, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    daily_limit = Column(Integer, default=0, nullable=False)
    total_limit = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PointLedger(Base):
    __tablename__ = "point_ledgers"
    __table_args__ = (
        UniqueConstraint("user_id", "rule_code", "reference_type", "reference_id", name="uq_point_ledger_event"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    rule_code = Column(String(64), nullable=False, index=True)
    reference_type = Column(String(64), nullable=False, index=True)
    reference_id = Column(Integer, nullable=False, index=True)
    points = Column(Integer, nullable=False)
    status = Column(String(16), default="active", nullable=False)
    note = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ShareEvent(Base):
    __tablename__ = "share_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    share_type = Column(String(32), default="mini_program", nullable=False)
    share_token = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PassLevelSetting(Base):
    __tablename__ = "pass_level_settings"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer, nullable=False, unique=True, index=True)
    name_zh = Column(String(64), nullable=False)
    name_en = Column(String(64), nullable=False)
    required_explore_points = Column(Integer, default=0, nullable=False)
    checkin_points = Column(Integer, default=0, nullable=False)
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
    checkin_distance_meters = Column(Integer, nullable=True)
    awarded_explore_points = Column(Integer, default=0, nullable=False)
    promoted_spot_image_id = Column(Integer, ForeignKey("spot_images.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("MiniProgramUser")
    spot = relationship("ScenicSpot")
    promoted_spot_image = relationship("SpotImage", foreign_keys=[promoted_spot_image_id])
