from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class ArchiveRequirement(Base):
    __tablename__ = "archive_requirements"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), nullable=False, unique=True, index=True)
    title = Column(String(160), nullable=False)
    module = Column(String(96), nullable=False, default="待确认模块")
    category = Column(String(32), nullable=False, index=True)
    version = Column(String(16), nullable=False, default="V1")
    priority = Column(String(16), nullable=False, default="中")
    status = Column(String(32), nullable=False, default="待确认", index=True)
    owner = Column(String(64), nullable=True)
    requester = Column(String(96), nullable=True)
    requester_user_id = Column(Integer, ForeignKey("mini_program_users.id"), nullable=True, index=True)
    source_type = Column(String(32), nullable=False, default="manual")
    source_date = Column(Date, nullable=False, index=True)
    source_text = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    acceptance_criteria = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=False, default="[]")
    planned_release = Column(Date, nullable=True)
    created_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tasks = relationship(
        "ArchiveDevelopmentTask",
        back_populates="requirement",
        cascade="all, delete-orphan",
        order_by="ArchiveDevelopmentTask.id",
    )
    events = relationship(
        "ArchiveEvent",
        back_populates="requirement",
        cascade="all, delete-orphan",
        order_by="ArchiveEvent.id",
    )


class ArchiveDevelopmentTask(Base):
    __tablename__ = "archive_development_tasks"
    __table_args__ = (
        UniqueConstraint("requirement_id", "sub_requirement_code", "title", name="uq_archive_task_round_title"),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), nullable=False, unique=True, index=True)
    requirement_id = Column(Integer, ForeignKey("archive_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    sub_requirement_code = Column(String(40), nullable=False, index=True)
    round_number = Column(Integer, nullable=False, default=0)
    title = Column(String(200), nullable=False)
    task_type = Column(String(32), nullable=False, default="综合开发")
    owner = Column(String(64), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="待开始", index=True)
    progress = Column(Integer, nullable=False, default=0)
    self_test_result = Column(String(16), nullable=True)
    self_test_detail = Column(Text, nullable=True)
    acceptance_result = Column(String(16), nullable=True)
    acceptance_detail = Column(Text, nullable=True)
    acceptance_notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    requirement = relationship("ArchiveRequirement", back_populates="tasks")


class ArchiveChatImport(Base):
    __tablename__ = "archive_chat_imports"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(255), nullable=False)
    source_type = Column(String(32), nullable=False, default="wechat_personal")
    contact = Column(String(96), nullable=True)
    raw_text = Column(Text, nullable=False)
    message_count = Column(Integer, nullable=False, default=0)
    recognized_count = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="processed")
    imported_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ArchiveEvent(Base):
    __tablename__ = "archive_events"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("archive_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("archive_development_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(48), nullable=False, index=True)
    actor_type = Column(String(32), nullable=False)
    actor_name = Column(String(96), nullable=True)
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    requirement = relationship("ArchiveRequirement", back_populates="events")


class ArchiveInternalMessage(Base):
    __tablename__ = "archive_internal_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_type = Column(String(32), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    content = Column(Text, nullable=False)
    related_requirement_id = Column(Integer, ForeignKey("archive_requirements.id", ondelete="CASCADE"), nullable=True, index=True)
    target_role = Column(String(32), nullable=False, default="admin")
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
