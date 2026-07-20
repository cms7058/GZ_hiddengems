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
    spot_code = Column(String(8), nullable=True, unique=True, index=True)
    name_zh = Column(String(128), nullable=False)
    name_en = Column(String(128), nullable=False)
    locked_name_zh = Column(String(128), nullable=True)
    locked_name_en = Column(String(128), nullable=True)
    summary_zh = Column(String(512), nullable=False)
    summary_en = Column(String(512), nullable=False)
    description_zh = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    city = Column(String(64), nullable=False)
    county = Column(String(64), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    river_name = Column(String(128), nullable=True)
    river_upstream_latitude = Column(Float, nullable=True)
    river_upstream_longitude = Column(Float, nullable=True)
    video_channel_urls_json = Column(Text, nullable=False, default="[]")
    visibility_level = Column(String(32), default="public", nullable=False)
    review_status = Column(String(32), default="draft", nullable=False)
    recommendation_level = Column(Integer, default=1, nullable=False)
    required_explore_points = Column(Integer, default=0, nullable=False)
    checkin_radius_meters = Column(Integer, default=300, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tags = relationship("Tag", secondary="spot_tags", back_populates="spots")
    travel_notes = relationship("TravelNote", back_populates="spot")
    comments = relationship("UserComment", back_populates="spot")
    lifestyle_recommendations = relationship("LifestyleRecommendation", back_populates="spot")
    spot_images = relationship("SpotImage", back_populates="spot")
    child_points = relationship(
        "SpotChildPoint",
        back_populates="spot",
        cascade="all, delete-orphan",
        order_by="SpotChildPoint.sort_order",
    )


class SpotChildPoint(Base):
    __tablename__ = "spot_child_points"

    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    note = Column(String(512), nullable=True)
    fetch_weather = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    spot = relationship("ScenicSpot", back_populates="child_points")
