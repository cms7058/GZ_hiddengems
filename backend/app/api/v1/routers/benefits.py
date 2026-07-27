from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.user import BenefitCatalog, BenefitPointLedger, MiniProgramUser, UserBenefitRedemption, UserSpotUnlock
from app.schemas.benefits import BenefitCatalogOut, RedemptionCreate, RedemptionOut, BenefitLedgerOut
from app.services.benefits import backfill_legacy_benefit_points, redeem_benefit, redemption_out

router = APIRouter()

@router.get("/catalog", response_model=list[BenefitCatalogOut])
def catalog(db: Session = Depends(get_db)):
    return list(db.scalars(select(BenefitCatalog).where(BenefitCatalog.is_active.is_(True)).order_by(BenefitCatalog.category, BenefitCatalog.id)).all())

@router.get("/me/{user_id}")
def my_benefits(user_id: int, db: Session = Depends(get_db)):
    user = db.get(MiniProgramUser, user_id)
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    if backfill_legacy_benefit_points(db, user):
        db.commit()
        db.refresh(user)
    redemptions = db.scalars(select(UserBenefitRedemption).options(joinedload(UserBenefitRedemption.benefit)).where(UserBenefitRedemption.user_id == user_id).order_by(UserBenefitRedemption.id.desc())).all()
    ledgers = db.scalars(select(BenefitPointLedger).where(BenefitPointLedger.user_id == user_id).order_by(BenefitPointLedger.id.desc()).limit(100)).all()
    unlocks = db.scalars(select(UserSpotUnlock).where(UserSpotUnlock.user_id == user_id, UserSpotUnlock.status == "active")).all()
    return {"explore_points": user.explore_points, "benefit_points": user.benefit_points, "redemptions": [redemption_out(x) for x in redemptions], "ledgers": ledgers, "unlocked_spot_ids": [x.spot_id for x in unlocks]}

@router.post("/redeem", response_model=RedemptionOut)
def redeem(payload: RedemptionCreate, db: Session = Depends(get_db)):
    user = db.get(MiniProgramUser, payload.user_id)
    benefit = db.get(BenefitCatalog, payload.benefit_id)
    if user is None or not user.is_active: raise HTTPException(status_code=404, detail="User not found")
    if benefit is None: raise HTTPException(status_code=404, detail="Benefit not found")
    redemption = redeem_benefit(db, user, benefit)
    db.commit(); db.refresh(redemption); db.refresh(redemption, attribute_names=["benefit"])
    return redemption_out(redemption)
