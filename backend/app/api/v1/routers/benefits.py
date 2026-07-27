from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.spot import ScenicSpot
from app.models.user import BenefitCatalog, BenefitPointLedger, MiniProgramUser, UserBenefitRedemption, UserSpotUnlock
from app.schemas.benefits import BatchRedemptionCreate, BatchRedemptionOut, BenefitCatalogOut, RedemptionCreate, RedemptionOut, SpotUnlockCandidateOut, BenefitLedgerOut
from app.services.benefits import backfill_legacy_benefit_points, ensure_spot_unlock_benefit, redeem_benefit, redemption_out
from app.services.localization import choose_text, normalize_language
from app.services.pass_levels import get_active_pass_settings_by_level, get_spot_unlock_state

router = APIRouter()

@router.get("/catalog", response_model=list[BenefitCatalogOut])
def catalog(db: Session = Depends(get_db)):
    return list(db.scalars(select(BenefitCatalog).where(BenefitCatalog.is_active.is_(True)).order_by(BenefitCatalog.category, BenefitCatalog.id)).all())


@router.get("/spot-unlocks/{user_id}", response_model=list[SpotUnlockCandidateOut])
def available_spot_unlocks(
    user_id: int,
    lang: str = "zh-CN",
    db: Session = Depends(get_db),
) -> list[SpotUnlockCandidateOut]:
    user = db.get(MiniProgramUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    changed = bool(backfill_legacy_benefit_points(db, user))
    settings_by_level = get_active_pass_settings_by_level(db)
    normalized_lang = normalize_language(lang)
    candidates: list[SpotUnlockCandidateOut] = []
    spots = db.scalars(
        select(ScenicSpot)
        .where(ScenicSpot.is_active.is_(True), ScenicSpot.review_status == "approved")
        .order_by(ScenicSpot.required_explore_points.asc(), ScenicSpot.recommendation_level.asc(), ScenicSpot.id.asc())
    ).all()
    for spot in spots:
        is_unlocked, required_points = get_spot_unlock_state(
            spot_required_explore_points=spot.required_explore_points,
            recommendation_level=spot.recommendation_level,
            user=user,
            fallback_explore_points=user.explore_points,
            settings_by_level=settings_by_level,
            spot_id=spot.id,
            db=db,
        )
        if required_points <= 0:
            continue
        benefit = ensure_spot_unlock_benefit(
            db,
            spot_id=spot.id,
            name_zh=spot.name_zh,
            name_en=spot.name_en,
            summary_zh=spot.summary_zh,
            summary_en=spot.summary_en,
            points_cost=required_points,
        )
        if is_unlocked:
            candidates.append(
                SpotUnlockCandidateOut(
                    benefit_id=benefit.id,
                    spot_id=spot.id,
                    name=choose_text(normalized_lang, spot.name_zh, spot.name_en),
                    summary=choose_text(normalized_lang, spot.summary_zh, spot.summary_en),
                    recommendation_level=spot.recommendation_level,
                    points_cost=benefit.points_cost,
                    valid_days=benefit.valid_days,
                    is_unlocked=True,
                )
            )
            continue
        if not benefit.is_active or benefit.points_cost > user.benefit_points:
            continue
        candidates.append(
            SpotUnlockCandidateOut(
                benefit_id=benefit.id,
                spot_id=spot.id,
                name=choose_text(normalized_lang, spot.name_zh, spot.name_en),
                summary=choose_text(normalized_lang, spot.summary_zh, spot.summary_en),
                recommendation_level=spot.recommendation_level,
                points_cost=benefit.points_cost,
                valid_days=benefit.valid_days,
                is_unlocked=False,
            )
        )
    if changed or candidates:
        db.commit()
    return candidates

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


@router.post("/redeem-batch", response_model=BatchRedemptionOut)
def redeem_spot_unlocks_batch(payload: BatchRedemptionCreate, db: Session = Depends(get_db)) -> BatchRedemptionOut:
    benefit_ids = list(dict.fromkeys(payload.benefit_ids))
    if len(benefit_ids) != len(payload.benefit_ids):
        raise HTTPException(status_code=400, detail="Duplicate benefit selection")
    user = db.get(MiniProgramUser, payload.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    benefits = db.scalars(select(BenefitCatalog).where(BenefitCatalog.id.in_(benefit_ids))).all()
    if len(benefits) != len(benefit_ids):
        raise HTTPException(status_code=404, detail="Benefit not found")
    if any(not benefit.is_active or benefit.category != "spot_unlock" for benefit in benefits):
        raise HTTPException(status_code=400, detail="Only active spot unlock benefits can be selected")
    total_cost = sum(benefit.points_cost for benefit in benefits)
    if total_cost > user.benefit_points:
        raise HTTPException(status_code=400, detail="Insufficient benefit points")
    redemptions = [redeem_benefit(db, user, benefit) for benefit in benefits]
    db.commit()
    for redemption in redemptions:
        db.refresh(redemption)
        db.refresh(redemption, attribute_names=["benefit"])
    return BatchRedemptionOut(
        redemptions=[redemption_out(redemption) for redemption in redemptions],
        benefit_points=user.benefit_points,
    )
