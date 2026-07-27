from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BenefitCatalogIn(BaseModel):
    category: str = Field(..., pattern="^(spot_unlock|food|advanced)$")
    benefit_type: str = Field(default="generic", max_length=32)
    name_zh: str = Field(..., max_length=128)
    name_en: str = Field(default="", max_length=128)
    description_zh: str = Field(default="", max_length=1024)
    description_en: str = Field(default="", max_length=1024)
    points_cost: int = Field(default=0, ge=0)
    spot_id: Optional[int] = None
    stock: int = Field(default=0, ge=0)
    valid_days: int = Field(default=30, ge=1, le=3650)
    is_active: bool = True


class BenefitCatalogOut(BenefitCatalogIn):
    id: int
    remaining_stock: Optional[int] = None
    class Config:
        from_attributes = True


class SpotUnlockCandidateOut(BaseModel):
    benefit_id: int
    spot_id: int
    name: str
    summary: str = ""
    recommendation_level: int
    points_cost: int
    valid_days: int
    is_unlocked: bool = False


class RedemptionCreate(BaseModel):
    user_id: int
    benefit_id: int


class BatchRedemptionCreate(BaseModel):
    user_id: int
    benefit_ids: list[int] = Field(min_length=1, max_length=50)


class RedemptionOut(BaseModel):
    id: int
    benefit_id: int
    benefit_name: str
    category: str
    points_cost: int
    status: str
    verification_code: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class BatchRedemptionOut(BaseModel):
    redemptions: list[RedemptionOut]
    benefit_points: int


class BenefitLedgerOut(BaseModel):
    id: int
    change_points: int
    action: str
    reference_type: str
    reference_id: int
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
