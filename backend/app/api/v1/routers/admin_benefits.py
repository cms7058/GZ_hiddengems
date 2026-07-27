from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.user import BenefitCatalog, BenefitPointLedger, MiniProgramUser, UserBenefitRedemption, UserSpotUnlock
from app.schemas.benefits import BenefitCatalogIn, BenefitCatalogOut
from app.services.benefits import redemption_out

router = APIRouter()

@router.get("/catalog", response_model=list[BenefitCatalogOut])
def list_catalog(db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)):
    return list(db.scalars(select(BenefitCatalog).order_by(BenefitCatalog.category, BenefitCatalog.id)).all())

@router.post("/catalog", response_model=BenefitCatalogOut, status_code=201)
def create_catalog(payload: BenefitCatalogIn, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)):
    item = BenefitCatalog(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.patch("/catalog/{benefit_id}", response_model=BenefitCatalogOut)
def update_catalog(benefit_id: int, payload: BenefitCatalogIn, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)):
    item = db.get(BenefitCatalog, benefit_id)
    if item is None: raise HTTPException(status_code=404, detail="Benefit not found")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

@router.delete("/catalog/{benefit_id}", status_code=204)
def delete_catalog(benefit_id: int, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)):
    item = db.get(BenefitCatalog, benefit_id)
    if item is None: raise HTTPException(status_code=404, detail="Benefit not found")
    db.delete(item); db.commit()

@router.get("/users/{user_id}")
def user_benefits(user_id: int, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)):
    user = db.get(MiniProgramUser, user_id)
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    redemptions = db.scalars(select(UserBenefitRedemption).options(joinedload(UserBenefitRedemption.benefit)).where(UserBenefitRedemption.user_id == user_id).order_by(UserBenefitRedemption.id.desc())).all()
    ledger = db.scalars(select(BenefitPointLedger).where(BenefitPointLedger.user_id == user_id).order_by(BenefitPointLedger.id.desc())).all()
    unlocks = db.scalars(select(UserSpotUnlock).where(UserSpotUnlock.user_id == user_id).order_by(UserSpotUnlock.id.desc())).all()
    return {"user_id": user.id, "explore_points": user.explore_points, "benefit_points": user.benefit_points, "redemptions": [redemption_out(item) for item in redemptions], "ledger": ledger, "unlocks": unlocks}
