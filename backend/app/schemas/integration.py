from typing import Optional

from pydantic import BaseModel, Field


class IntegrationSettingOut(BaseModel):
    id: int
    group: str
    key: str
    value: Optional[str] = None
    label_zh: str
    label_en: str
    input_type: str
    is_secret: bool
    sort_order: int
    is_configured: bool

    class Config:
        from_attributes = True


class IntegrationGroupOut(BaseModel):
    group: str
    title_zh: str
    title_en: str
    description_zh: str
    description_en: str
    settings: list[IntegrationSettingOut]


class IntegrationGroupUpdate(BaseModel):
    settings: dict[str, Optional[str]] = Field(default_factory=dict)
