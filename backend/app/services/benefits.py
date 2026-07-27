from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import BenefitCatalog, BenefitPointLedger, MiniProgramUser, UserBenefitRedemption, UserSpotUnlock


def ensure_spot_unlock_benefit(
    db: Session,
    *,
    spot_id: int,
    name_zh: str,
    name_en: str,
    summary_zh: str,
    summary_en: str,
    points_cost: int,
) -> BenefitCatalog:
    """Return an admin-defined unlock benefit, or create the default one."""
    benefit = db.scalar(
        select(BenefitCatalog)
        .where(BenefitCatalog.category == "spot_unlock", BenefitCatalog.spot_id == spot_id)
        .order_by(BenefitCatalog.id.asc())
    )
    if benefit is not None:
        return benefit
    benefit = BenefitCatalog(
        category="spot_unlock",
        benefit_type="spot_unlock",
        name_zh=name_zh,
        name_en=name_en or name_zh,
        description_zh=summary_zh or "使用权益积分解锁该秘境。",
        description_en=summary_en or "Use benefit points to unlock this hidden gem.",
        points_cost=points_cost,
        spot_id=spot_id,
        stock=0,
        valid_days=3650,
        is_active=True,
    )
    db.add(benefit)
    db.flush()
    return benefit


def backfill_legacy_benefit_points(db: Session, user: MiniProgramUser) -> int:
    """Migrate pre-benefit accounts once without restoring spent balances."""
    if user.explore_points <= 0 or user.benefit_points > 0:
        return 0
    has_ledger = db.scalar(
        select(BenefitPointLedger.id)
        .where(BenefitPointLedger.user_id == user.id)
        .limit(1)
    )
    if has_ledger is not None:
        return 0
    user.benefit_points = user.explore_points
    db.add(
        BenefitPointLedger(
            user_id=user.id,
            change_points=user.explore_points,
            action="migration",
            reference_type="legacy_balance",
            reference_id=user.id,
            note="历史探秘积分迁移为可用权益积分",
        )
    )
    return user.explore_points


def adjust_benefit_points_for_admin(
    db: Session,
    user: MiniProgramUser,
    previous_explore_points: int,
    previous_benefit_points: int,
    update_data: dict,
) -> int:
    """Apply administrator corrections to available points unless overridden."""
    requested_explore = int(update_data.get("explore_points", user.explore_points))
    requested_benefit = update_data.get("benefit_points")
    benefit_unchanged = requested_benefit is None or int(requested_benefit) == previous_benefit_points
    if "explore_points" in update_data and benefit_unchanged:
        target = max(0, previous_benefit_points + requested_explore - previous_explore_points)
    elif requested_benefit is not None:
        target = int(requested_benefit)
    else:
        return 0

    change = target - previous_benefit_points
    user.benefit_points = target
    if change:
        db.add(
            BenefitPointLedger(
                user_id=user.id,
                change_points=change,
                action="admin_adjust",
                reference_type="admin_user_update",
                reference_id=user.id,
                note="管理员调整用户积分",
            )
        )
    return change


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
