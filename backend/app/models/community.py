from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import MEDIUMTEXT

from app.db.base import Base


class CommunityUpload(Base):
    __tablename__ = "community_uploads"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    purpose = Column(String(16), nullable=False)
    media_type = Column(String(16), nullable=False)
    media_url = Column(String(512), nullable=True)
    duration = Column(Float, nullable=False, default=0)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    frames_json = Column(Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False, default="[]")
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class EcoSubmission(Base):
    __tablename__ = "eco_submissions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=False, index=True)
    level = Column(Integer, nullable=False)
    category = Column(String(1), nullable=False)
    upload_id = Column(Integer, ForeignKey("community_uploads.id"), nullable=False, unique=True)
    status = Column(String(16), nullable=False, default="pending")
    verdict = Column(String(24), nullable=True)
    review_note = Column(String(512), nullable=False, default="")
    reviewer_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    ai_status = Column(String(24), nullable=False, default="not_required")
    ai_note = Column(Text, nullable=False, default="")
    penalized = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)


class EcoCredit(Base):
    __tablename__ = "eco_credits"
    __table_args__ = (UniqueConstraint("user_id", "spot_id", name="uq_eco_credit_spot"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=False)
    level = Column(Integer, nullable=False)
    submission_id = Column(Integer, ForeignKey("eco_submissions.id"), nullable=False, unique=True)
    credit_active = Column(Boolean, nullable=False, default=True)
    checkin_active = Column(Boolean, nullable=False, default=True)


class EcoWarning(Base):
    __tablename__ = "eco_warnings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    trigger_submission_id = Column(Integer, ForeignKey("eco_submissions.id"), nullable=False, unique=True)
    reason = Column(String(32), nullable=False)
    submission_ids_json = Column(Text, nullable=False)
    cleared_credits = Column(Integer, nullable=False)
    cleared_checkins = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class EcoMilestone(Base):
    __tablename__ = "eco_milestones"
    __table_args__ = (UniqueConstraint("user_id", "target_level", name="uq_eco_milestone"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    target_level = Column(Integer, nullable=False)
    spot_ids_json = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class FoodPolicy(Base):
    __tablename__ = "food_policies"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    all_users = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    min_photos = Column(Integer, nullable=False, default=1)
    max_photos = Column(Integer, nullable=False, default=3)
    max_image_bytes = Column(Integer, nullable=False, default=2097152)
    max_width = Column(Integer, nullable=False, default=4096)
    max_height = Column(Integer, nullable=False, default=4096)
    video_required = Column(Boolean, nullable=False, default=False)
    max_video_seconds = Column(Integer, nullable=False, default=3)
    reward_points = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class FoodPolicyUser(Base):
    __tablename__ = "food_policy_users"
    policy_id = Column(Integer, ForeignKey("food_policies.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), primary_key=True)


class FoodSubmission(Base):
    __tablename__ = "food_submissions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("food_policies.id"), nullable=False)
    policy_json = Column(Text, nullable=False)
    title = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    upload_ids_json = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    review_note = Column(String(512), nullable=False, default="")
    reward_points = Column(Integer, nullable=False)
    reviewer_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
