from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import BenefitCatalog, BenefitPointLedger, MiniProgramUser, UserBenefitRedemption, UserSpotUnlock


def redeem_benefit(db: Session, user: MiniProgramUser, benefit: BenefitCatalog) -> UserBenefitRedemption:
    if not benefit.is_active:
        raise HTTPException(status_code=400, detail="Benefit is unavailable")
    if benefit.stock > 0:
        used = db.scalar(select(func.count(UserBenefitRedemption.id)).where(UserBenefitRedemption.benefit_id == benefit.id, UserBenefitRedemption.status.in_(("confirmed", "used")))) or 0
        if used >= benefit.stock:
            raise HTTPException(status_code=400, detail="Benefit is out of stock")
    if user.benefit_points < benefit.points_cost:
        raise HTTPException(status_code=400, detail="Insufficient benefit points")
    if benefit.category == "spot_unlock":
        if benefit.spot_id is None:
            raise HTTPException(status_code=400, detail="Spot unlock benefit is not linked to a spot")
        existing = db.scalar(select(UserSpotUnlock.id).where(UserSpotUnlock.user_id == user.id, UserSpotUnlock.spot_id == benefit.spot_id, UserSpotUnlock.status == "active"))
        if existing is not None:
            raise HTTPException(status_code=409, detail="Spot is already unlocked for this user")
    expires_at = datetime.now(timezone.utc) + timedelta(days=benefit.valid_days)
    code = token_urlsafe(8).upper() if benefit.category == "food" else None
    redemption = UserBenefitRedemption(user_id=user.id, benefit_id=benefit.id, points_cost=benefit.points_cost, expires_at=expires_at, verification_code=code)
    db.add(redemption)
    db.flush()
    user.benefit_points -= benefit.points_cost
    db.add(BenefitPointLedger(user_id=user.id, change_points=-benefit.points_cost, action="redeem", reference_type="benefit_redemption", reference_id=redemption.id, note=benefit.name_zh))
    if benefit.category == "spot_unlock":
        db.add(UserSpotUnlock(user_id=user.id, spot_id=benefit.spot_id, redemption_id=redemption.id, status="active"))
    return redemption


def redemption_out(redemption: UserBenefitRedemption) -> dict:
    return {
        "id": redemption.id,
        "benefit_id": redemption.benefit_id,
        "benefit_name": redemption.benefit.name_zh,
        "category": redemption.benefit.category,
        "points_cost": redemption.points_cost,
        "status": redemption.status,
        "verification_code": redemption.verification_code,
        "expires_at": redemption.expires_at,
        "created_at": redemption.created_at,
    }
