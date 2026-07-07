from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint, func

from app.db.base import Base


class IntegrationSetting(Base):
    __tablename__ = "integration_settings"
    __table_args__ = (UniqueConstraint("group", "key", name="uq_integration_group_key"),)

    id = Column(Integer, primary_key=True, index=True)
    group = Column(String(32), nullable=False, index=True)
    key = Column(String(96), nullable=False, index=True)
    value = Column(Text, nullable=True)
    label_zh = Column(String(128), nullable=False)
    label_en = Column(String(128), nullable=False)
    input_type = Column(String(32), default="text", nullable=False)
    is_secret = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
