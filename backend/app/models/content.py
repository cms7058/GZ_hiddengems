from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class SpotImage(Base):
    __tablename__ = "spot_images"

    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=False, index=True)
    image_url = Column(String(512), nullable=False)
    media_type = Column(String(32), default="image", nullable=False)
    caption = Column(String(256), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_cover = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    spot = relationship("ScenicSpot", back_populates="spot_images")


class TravelNote(Base):
    __tablename__ = "travel_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=True, index=True)
    title = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(512), nullable=True)
    status = Column(String(32), default="pending", nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("MiniProgramUser")
    spot = relationship("ScenicSpot", back_populates="travel_notes")


class ContentMedia(Base):
    __tablename__ = "content_media"

    id = Column(Integer, primary_key=True, index=True)
    owner_type = Column(String(32), nullable=False, index=True)
    owner_id = Column(Integer, nullable=False, index=True)
    media_url = Column(String(512), nullable=False)
    media_type = Column(String(32), default="image", nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserComment(Base):
    __tablename__ = "user_comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=True, index=True)
    content = Column(String(512), nullable=False)
    image_url = Column(String(512), nullable=True)
    status = Column(String(32), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("MiniProgramUser")
    spot = relationship("ScenicSpot", back_populates="comments")
    likes = relationship("CommentLike", back_populates="comment", cascade="all, delete-orphan")


class CommentLike(Base):
    __tablename__ = "comment_likes"
    __table_args__ = (UniqueConstraint("comment_id", "user_id", name="uq_comment_like_user"),)

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("user_comments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    comment = relationship("UserComment", back_populates="likes")
    user = relationship("MiniProgramUser")


class SpotRecommendation(Base):
    __tablename__ = "spot_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    name_zh = Column(String(128), nullable=False)
    name_en = Column(String(128), nullable=False)
    summary_zh = Column(String(512), nullable=False)
    summary_en = Column(String(512), nullable=False)
    description_zh = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    city = Column(String(64), nullable=False)
    county = Column(String(64), nullable=False)
    latitude = Column(String(32), nullable=True)
    longitude = Column(String(32), nullable=True)
    river_name = Column(String(128), nullable=True)
    river_upstream_latitude = Column(String(32), nullable=True)
    river_upstream_longitude = Column(String(32), nullable=True)
    recommendation_level = Column(Integer, default=0, nullable=False)
    tag_ids_json = Column(Text, default="[]", nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    review_note = Column(String(512), nullable=True)
    approved_spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("MiniProgramUser")
    approved_spot = relationship("ScenicSpot")


class LifestyleRecommendation(Base):
    __tablename__ = "lifestyle_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=True, index=True)
    category = Column(String(32), nullable=False, index=True)
    name_zh = Column(String(128), nullable=False)
    name_en = Column(String(128), nullable=False)
    summary_zh = Column(String(512), nullable=False)
    summary_en = Column(String(512), nullable=False)
    city = Column(String(64), nullable=False)
    county = Column(String(64), nullable=False)
    address = Column(String(256), nullable=True)
    contact = Column(String(128), nullable=True)
    image_url = Column(String(512), nullable=True)
    price_level = Column(String(32), default="mid", nullable=False)
    recommendation_level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    spot = relationship("ScenicSpot", back_populates="lifestyle_recommendations")
