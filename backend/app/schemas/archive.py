from typing import Literal, Optional

from pydantic import BaseModel, Field


ArchiveCategory = Literal["新功能", "需求变更", "缺陷", "确认信息", "验证反馈"]
ArchiveResult = Literal["通过", "未通过"]


class ArchiveRequirementCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    module: str = Field(default="待确认模块", max_length=96)
    category: ArchiveCategory
    priority: Literal["紧急", "高", "中", "低"] = "中"
    requester: Optional[str] = Field(default=None, max_length=96)
    source_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    source_text: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    acceptance_criteria: str = Field(..., min_length=1)
    owner: Optional[str] = Field(default=None, max_length=64)
    planned_release: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    evidence: list[str] = Field(default_factory=list, max_length=20)


class ArchiveRequirementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    module: Optional[str] = Field(default=None, max_length=96)
    category: Optional[ArchiveCategory] = None
    priority: Optional[Literal["紧急", "高", "中", "低"]] = None
    status: Optional[str] = Field(default=None, max_length=32)
    requester: Optional[str] = Field(default=None, max_length=96)
    source_text: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    owner: Optional[str] = Field(default=None, max_length=64)
    planned_release: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    evidence: Optional[list[str]] = Field(default=None, max_length=20)


class ArchiveChatImportIn(BaseModel):
    source_name: str = Field(default="微信聊天粘贴", max_length=255)
    source_type: Literal["wechat_personal", "wechat_work", "text", "image", "audio"] = "wechat_personal"
    contact: Optional[str] = Field(default=None, max_length=96)
    raw_text: str = Field(..., min_length=1, max_length=100_000)
    evidence: list[str] = Field(default_factory=list, max_length=50)


class ArchiveSelfTestIn(BaseModel):
    result: ArchiveResult
    detail: str = Field(default="", max_length=4000)


class ArchiveAcceptanceIn(BaseModel):
    result: ArchiveResult
    detail: str = Field(default="", max_length=4000)


class ArchiveAssistantCommandIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ArchiveAssistantSubmitIn(BaseModel):
    category: ArchiveCategory
    module: str = Field(default="待确认模块", max_length=96)
    title: str = Field(..., min_length=2, max_length=160)
    description: str = Field(..., min_length=1, max_length=8000)
    acceptance_criteria: str = Field(default="由管理员补充可验证的验收标准。", max_length=8000)
    priority: Literal["紧急", "高", "中", "低"] = "中"
    requester: Optional[str] = Field(default=None, max_length=96)
    evidence: list[str] = Field(default_factory=list, max_length=20)


class MiniArchiveAssistantSubmitIn(ArchiveAssistantSubmitIn):
    user_id: int = Field(..., ge=1)


class MiniArchiveAcceptanceIn(BaseModel):
    user_id: int = Field(..., ge=1)
    full_requirement_code: str = Field(..., pattern=r"^REQ-\d{8}-\d{3}(?:-\d+)?$")
    result: ArchiveResult
    detail: str = Field(default="", max_length=4000)
