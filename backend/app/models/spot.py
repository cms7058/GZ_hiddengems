from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class SpotTag(Base):
    __tablename__ = "spot_tags"

    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name_zh = Column(String(64), nullable=False)
    name_en = Column(String(64), nullable=False)
    icon = Column(String(64), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    spots = relationship("ScenicSpot", secondary="spot_tags", back_populates="tags")


class ScenicSpot(Base):
    __tablename__ = "scenic_spots"

    id = Column(Integer, primary_key=True, index=True)
    name_zh = Column(String(128), nullable=False)
    name_en = Column(String(128), nullable=False)
    summary_zh = Column(String(512), nullable=False)
    summary_en = Column(String(512), nullable=False)
    description_zh = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    city = Column(String(64), nullable=False)
    county = Column(String(64), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    visibility_level = Column(String(32), default="public", nullable=False)
    review_status = Column(String(32), default="draft", nullable=False)
    recommendation_level = Column(Integer, default=1, nullable=False)
    checkin_radius_meters = Column(Integer, default=300, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tags = relationship("Tag", secondary="spot_tags", back_populates="spots")
