from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class SpotImage(Base):
    __tablename__ = "spot_images"

    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=False, index=True)
    image_url = Column(String(512), nullable=False)
    caption = Column(String(256), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_cover = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    spot = relationship("ScenicSpot")


class TravelNote(Base):
    __tablename__ = "travel_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=True, index=True)
    title = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("MiniProgramUser")
    spot = relationship("ScenicSpot")


class UserComment(Base):
    __tablename__ = "user_comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("scenic_spots.id"), nullable=True, index=True)
    content = Column(String(512), nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("MiniProgramUser")
    spot = relationship("ScenicSpot")


class LifestyleRecommendation(Base):
    __tablename__ = "lifestyle_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(32), nullable=False, index=True)
    name_zh = Column(String(128), nullable=False)
    name_en = Column(String(128), nullable=False)
    summary_zh = Column(String(512), nullable=False)
    summary_en = Column(String(512), nullable=False)
    city = Column(String(64), nullable=False)
    county = Column(String(64), nullable=False)
    address = Column(String(256), nullable=True)
    contact = Column(String(128), nullable=True)
    price_level = Column(String(32), default="mid", nullable=False)
    recommendation_level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
